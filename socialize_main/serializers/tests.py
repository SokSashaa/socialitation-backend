from rest_flex_fields import FlexFieldsModelSerializer
from rest_framework import serializers

from socialize_main.models import User, Tests, TestQuestions, Answers, TestObservered, TestResult, ObservedAnswer

class GetUserTestsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text='ID юзера')


class TestsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tests
        fields = ('id', 'title', 'description', 'created_at')
        read_only_fields = ['id']


class SingleTestCreateSerializer(serializers.Serializer):
    questions = serializers.JSONField()


class CreateTestSerializer(serializers.Serializer):
    title = serializers.CharField(help_text='Заголовок теста')
    description = serializers.CharField(help_text='Описание теста', required=False, allow_null=True, allow_blank=True) #  TODO ЗАЛИТЬ


class SingleTestSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='ID теста', source='pk')
    title = serializers.CharField(help_text='Заголовок теста')
    created_at = serializers.DateTimeField(help_text='Дата создания теста')
    description = serializers.CharField(help_text='Описание теста')
    questions = serializers.SerializerMethodField()

    def get_questions(self, obj):
        questions = TestQuestions.objects.filter(test=obj)
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
        print(self.context)
        observed_id = self.context.get('user_id')
        if request:
            print(f"Request is present: {request}")
        if observed_id:
            print(f"Observed ID: {observed_id}")
        if observed_id:
            try:
                test_obs = TestObservered.objects.get(test=obj, observed__user__pk=observed_id)
                return test_obs.is_passed
            except TestObservered.DoesNotExist:
                print(f"TestObservered not found for test ID: {obj.pk} and user ID: {observed_id}")
                return None
        else:
            return None

    def get_questions(self, obj):
        questions = TestQuestions.objects.filter(test=obj)
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
        answers = Answers.objects.filter(question=obj)
        return AnswersSerializer(answers, many=True).data


class AppointTestSerializer(serializers.Serializer):
    link = serializers.ListField(help_text='Список юзеров для привязки', child=serializers.IntegerField())
    unlink = serializers.ListField(help_text='Список юзеров для отвязки', child=serializers.IntegerField())
    test_id = serializers.IntegerField(help_text='Тест для действий')


class UserTestsSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(help_text='ID пользователя', source='pk')
    tests = serializers.SerializerMethodField()

    def get_tests(self, obj):
        tests_obs = list(TestObservered.objects.filter(observed=obj.observed_user.first().pk).values_list('test__id', flat=True))
        tests = Tests.objects.filter(pk__in=tests_obs)
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
    answers = AnswerSerializer(many=True, read_only=True, source='answer_question')
    answer_user = serializers.SerializerMethodField()

    class Meta:
        model = TestQuestions
        fields = ('id', 'title', 'type', 'answers', 'answer_user')

    def get_answer_user(self, obj):
        request = self.context.get('request')
        print(self.context)
        if request:
            print(request.data)
            user_id = request.data.get('user_id')
            if user_id:
                try:
                    user = User.objects.get(pk=user_id)
                except User.DoesNotExist:
                    return None
                try:
                    test_result = TestResult.objects.get(test=obj.test, observed=user.observed_user.first())
                    observed_answer = list(ObservedAnswer.objects.filter(test_result=test_result, answer__question=obj).values_list('answer__id', flat=True))
                    answers = Answers.objects.filter(pk__in=observed_answer)
                    return AnswerSerializer(answers, many=True).data
                except (TestResult.DoesNotExist, ObservedAnswer.DoesNotExist):
                    return None
        return None


class TestSerializer(serializers.ModelSerializer):
    questions = TestQuestionSerializer(many=True, read_only=True, source='test_question_test')

    class Meta:
        model = Tests
        fields = ('id', 'title', 'description', 'questions')

class GetAnswersSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    test_id = serializers.IntegerField()
