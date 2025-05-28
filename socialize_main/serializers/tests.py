from collections import defaultdict

from rest_framework import serializers

from socialize_main.models import User, Tests, TestQuestions, Answers, TestObservered, TestResult, ObservedAnswer
from socialize_main.utils.tests.get_answers import get_answers
from socialize_main.utils.tests.get_questions import get_questions
from socialize_main.utils.tests.get_tests_user_in_test_observered import get_tests_user_in_test_observered


class GetUserTestsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text='ID юзера')
    search = serializers.CharField(required=False, allow_null=True, allow_blank=True, help_text='Название для поиска')


class TestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tests
        fields = ('id', 'title', 'description', 'created_at')
        read_only_fields = ['id']


class SingleTestCreateSerializer(serializers.Serializer):
    questions = serializers.JSONField()


class CreateTestSerializer(serializers.Serializer):
    title = serializers.CharField(help_text='Заголовок теста')
    description = serializers.CharField(help_text='Описание теста', required=False, allow_null=True,
                                        allow_blank=True)  # TODO ЗАЛИТЬ


class SingleTestSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='ID теста', source='pk')
    title = serializers.CharField(help_text='Заголовок теста')
    created_at = serializers.DateTimeField(help_text='Дата создания теста')
    description = serializers.CharField(help_text='Описание теста')
    questions = serializers.SerializerMethodField()

    def get_questions(self, obj):
        questions = get_questions(obj)

        return QuestionSerializer(questions, many=True).data


class SingleTestUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='ID теста', source='pk')
    title = serializers.CharField(help_text='Заголовок теста')
    created_at = serializers.DateTimeField(help_text='Дата создания теста')
    description = serializers.CharField(help_text='Описание теста')
    questions = serializers.SerializerMethodField()
    is_passed = serializers.SerializerMethodField()

    def get_is_passed(self, obj):
        request = self.context.get('request')

        observed_id = self.context.get('user_id')

        if observed_id:
            try:
                test_obs = getattr(obj, '_prefetched_test_observer', None)

                if test_obs is None:
                    test_obs = TestObservered.objects.get(test=obj, observed__user__pk=observed_id)
                if test_obs:
                    return test_obs.is_passed

                return None
            except TestObservered.DoesNotExist:
                print(f"TestObservered not found for test ID: {obj.pk} and user ID: {observed_id}")
                return None
        else:
            return None

    def get_questions(self, obj):
        questions = get_questions(obj)

        return QuestionSerializer(questions, many=True, context=self.context).data


class AnswersSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='ID ответа', required=False)
    text = serializers.CharField(help_text='Текст ответа')
    point = serializers.IntegerField(help_text='Очки')


class QuestionsSerializer(serializers.Serializer):
    title = serializers.CharField(help_text='Заголовок вопроса')
    type = serializers.CharField(help_text='Тип ввода')
    required = serializers.BooleanField(help_text='Обязательность')
    answers = AnswersSerializer(many=True)


class ExistingTestSerializer(serializers.Serializer):
    title = serializers.CharField(help_text='Заголовок теста')
    description = serializers.CharField(help_text='Описание теста', required=False, allow_null=True, allow_blank=True)
    questions = QuestionsSerializer(many=True)


class QuestionSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='ID вопроса', source='pk')
    title = serializers.CharField(help_text='Заголовок вопроса')
    type = serializers.CharField(help_text='Тип ввода')
    required = serializers.BooleanField(help_text='Обязательность')
    answers = serializers.SerializerMethodField()

    def get_answers(self, obj):
        answers = get_answers(obj)

        return AnswersSerializer(answers, many=True).data


class AppointTestSerializer(serializers.Serializer):
    link = serializers.ListField(help_text='Список юзеров для привязки', child=serializers.IntegerField())
    unlink = serializers.ListField(help_text='Список юзеров для отвязки', child=serializers.IntegerField())
    test_id = serializers.IntegerField(help_text='Тест для действий')


class UserTestsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text='ID пользователя', source='pk')
    tests = serializers.SerializerMethodField()

    def get_tests(self, obj):
        tests = getattr(obj, '_prefetched_test_observers', None)
        if tests is None:
            tests = get_tests_user_in_test_observered(obj.pk)

        return SingleTestUserSerializer(tests, many=True, context=self.context).data


class TestObsSerializer(serializers.Serializer):
    test = SingleTestSerializer()


class SendAnswersSerializer(serializers.Serializer):
    test_id = serializers.IntegerField(help_text='ID теста')
    user_id = serializers.IntegerField(help_text='ID юзера')
    answers = serializers.ListField(help_text='Список ответов', child=serializers.IntegerField())


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answers
        fields = ('id', 'text', 'point')


class TestQuestionSerializer(serializers.ModelSerializer):
    answers = serializers.SerializerMethodField()
    answer_user = serializers.SerializerMethodField()

    class Meta:
        model = TestQuestions
        fields = ('id', 'title', 'type', 'answers', 'answer_user')

    def get_answers(self, obj):
        answers = get_answers(obj)

        return AnswersSerializer(answers, many=True, read_only=True).data

    def get_answer_user(self, obj):
        user = self.context.get('user')
        observed = self.context.get('observed')
        answers = self.context.get('answers')
        test_result = self.context.get('test_result')
        request = self.context.get('request')

        try:
            if not answers:
                if request:
                    if not user:
                        user_id = request.data.get('user_id')

                        if user_id:
                            user = User.objects.get(pk=user_id)

                            # Если будет заход еще раз, то user контексте будет,
                            # в нынешней ситуации не изменится при заходе ещё раз
                            self.context['user'] = user

                    if not observed:
                        observed = user.observed_user.first()
                        self.context['observed'] = observed

                    if not test_result:
                        test_result = TestResult.objects.get(test=obj.test, observed=observed)
                        self.context['test_result'] = test_result

                    if hasattr(obj, '_prefetched_user_answer_question'):
                        answers = obj._prefetched_user_answer_question
                    else:
                        answers = Answers.objects.filter(
                            observedanswer__test_result=test_result,
                            observedanswer__test_result__observed=observed,
                            question=obj
                        ).distinct()

            return AnswerSerializer(answers, many=True).data

        except (TestResult.DoesNotExist, ObservedAnswer.DoesNotExist, User.DoesNotExist):
            return None


class TestSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Tests
        fields = ('id', 'title', 'description', 'questions')

    def get_questions(self, obj):
        questions = get_questions(obj)
        answers = self.context.get('answers')

        if not answers:
            observed = self.context.get('observed')

            answers = Answers.objects.filter(
                observedanswer__test_result__test=obj,
                observedanswer__test_result__observed=observed
            ).select_related('question')

            answers_by_question = defaultdict(list)

            for answer in answers:
                answers_by_question[answer.question_id].append(answer)

            for question in questions:
                question._prefetched_user_answer_question = answers_by_question.get(question.id, [])

        return TestQuestionSerializer(questions, many=True, read_only=True, context=self.context).data


class GetAnswersSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    test_id = serializers.IntegerField()
