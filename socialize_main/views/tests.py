from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from socialize_main.constants.roles import Roles
from socialize_main.models import Tests, TestQuestions, Answers, TestObservered, User, TestResult, ObservedAnswer, \
    Observed
from socialize_main.permissions.check_attached_observed_permission import CheckAttachedObservedPermission
from socialize_main.permissions.role_permission import RolePermission
from socialize_main.permissions.user_access_control_permission import UserAccessControlPermission
from socialize_main.serializers.tests import GetUserTestsSerializer, GetAnswersSerializer, TestsSerializer, \
    UserTestsSerializer, TestSerializer, AppointTestSerializer, SingleTestSerializer, ExistingTestSerializer, \
    CreateTestSerializer, SendAnswersSerializer
from socialize_main.utils.tests.get_tests_user_in_test_observered import get_tests_user_in_test_observered


class TestsView(viewsets.ModelViewSet):
    serializer_class = TestsSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    ordering = ['-created_at']
    search_fields = ['title']
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['get_single_test', 'send_answers']:  # get_user_tests
            return [IsAuthenticated()]
        if self.action in ['get_user_tests']:
            return [UserAccessControlPermission()]
        if self.action in ['get_answers']:
            return [CheckAttachedObservedPermission()]
        return [RolePermission([Roles.ADMINISTRATOR.value, Roles.TUTOR.value])]

    def get_queryset(self):
        try:
            queryset = Tests.objects.all()
        except AttributeError:
            queryset = Tests.objects.none()
        return queryset

    @action(methods=['GET'], detail=True)
    def get_single_test(self, request, pk):
        try:
            test = (Tests.objects
                    .prefetch_related(
                Prefetch(
                    'test_question_test',
                    queryset=TestQuestions.objects.prefetch_related(
                        Prefetch(
                            'answer_question',
                            queryset=Answers.objects.all(),
                            to_attr='_prefetched_answers'
                        )
                    ),
                    to_attr='_prefetched_questions'
                )
            ).get(pk=pk))

            return JsonResponse({'success': True, 'result': SingleTestSerializer(test).data}, status=status.HTTP_200_OK)
        except Tests.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Не удалось найти тест']},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False, serializer_class=CreateTestSerializer)
    def create_test(self, request):
        serializer = CreateTestSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': [serializer.errors]}, status=status.HTTP_400_BAD_REQUEST)
        test, created = Tests.objects.get_or_create(
            title=serializer.validated_data['title'],
            defaults={
                'description': serializer.validated_data['description'] if serializer.validated_data.get(
                    'description') else ''
            }
        )
        if created:
            return JsonResponse({'sucsess': True, 'result': SingleTestSerializer(test).data}, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'success': False, 'errors': ['Тест с таким заголовком уже существует']},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=True, serializer_class=ExistingTestSerializer)
    def create_questions(self, request, pk):
        serializer = ExistingTestSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        test = Tests.objects.get(pk=pk)
        test.title = serializer.validated_data['title']
        test.description = serializer.validated_data['description'] if serializer.validated_data.get(
            'description') else ''
        test.test_question_test.all().delete()
        test.save()
        for question in serializer.validated_data['questions']:
            question_q, created_q = TestQuestions.objects.get_or_create(
                test=test,
                title=question['title'],
                type=question['type'],
                required=question['required']
            )
            question_q.answer_question.all().delete()
            question_q.save()
            for answer in question['answers']:
                answer_w, created_a = Answers.objects.get_or_create(
                    question=question_q,
                    text=answer['text'],
                    point=answer['point']
                )
        return JsonResponse({'success': True, 'result': SingleTestSerializer(test).data}, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    def appoint_test(self, request):
        serializer = AppointTestSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'sucsess': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            test = Tests.objects.get(pk=serializer.validated_data['test_id'])
            response = ''
            for link_user in serializer.validated_data['link']:
                user = User.objects.get(pk=link_user)
                test_observed, created = TestObservered.objects.get_or_create(
                    test=test,
                    observed=user.observed_user.first()
                )
                if not created:
                    response += user.name + '. '
            for unlink_user in serializer.validated_data['unlink']:
                user = User.objects.get(pk=unlink_user)
                try:
                    TestObservered.objects.get(test=test, observed=user.observed_user.first()).delete()  # TODO ЗАЛИТЬ
                except TestObservered.DoesNotExist:
                    continue
            if not response:
                return JsonResponse({'success': True}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': True, 'message': f'Пользователям: {response} тест уже назначен'},
                                    status=status.HTTP_200_OK)
        except Tests.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Тест не найден']}, status=status.HTTP_400_BAD_REQUEST)
        except Tests.MultipleObjectsReturned:
            return JsonResponse({'success': False,
                                 'errors': [f'Найдено несколько тестов по id: {serializer.validated_data["test_id"]}']},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['GET'], detail=False)
    def get_user_tests(self, request):
        serializer = GetUserTestsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = serializer.validated_data['user_id']

            user = User.objects.get(pk=user_id)

            user._prefetched_test_observers = get_tests_user_in_test_observered(user_id)

            context = {
                'request': request,
                'user_id': user_id,
            }
            return JsonResponse({'success': True, 'result': UserTestsSerializer(user, context=context).data},
                                status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Пользователь не найден']},
                                status=status.HTTP_400_BAD_REQUEST)
        except User.MultipleObjectsReturned:
            return JsonResponse({'success': False, 'errors': [
                f'Найдено несколько пользователей по id: {serializer.validated_data["user_id"]}']},
                                status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=False)
    def send_answers(self, request):
        serializer = SendAnswersSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                user_id = serializer.validated_data['user_id']

                test = Tests.objects.get(pk=serializer.validated_data['test_id'])

                user = User.objects.prefetch_related(
                    Prefetch(
                        'observed_user',
                        queryset=Observed.objects.all(),
                        to_attr='_prefetched_observed'
                    )
                ).get(pk=user_id)

                observed = user._prefetched_observed[0]  # В массиве 1 элемент всегда

                test_result = TestResult.objects.create(test=test, observed=observed)

                answer_ids = serializer.validated_data['answers']  # массив ответов
                answers = Answers.objects.filter(pk__in=answer_ids)

                if len(answer_ids) != len(answers):
                    existing_ids = set(answers.values_list('pk', flat=True))
                    missing = set(answer_ids) - existing_ids

                    return JsonResponse(
                        {'success': False, 'errors': f'Ответы не найдены: {missing}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                observed_answers = [
                    ObservedAnswer(
                        test_result=test_result,
                        answer=answer
                    ) for answer in answers
                ]

                ObservedAnswer.objects.bulk_create(observed_answers)

                test_observed = TestObservered.objects.update_or_create(
                    test=test, observed=observed,
                    defaults={
                        'is_passed': True
                    }
                )

                tests_contex = {
                    'request': request,
                    'user': user,
                    'observed': observed,
                    'answers': answers,
                    'test_result': test_result,
                }

                return JsonResponse(
                    {'success': True, 'result': TestSerializer(test, context=tests_contex).data},
                    status=status.HTTP_200_OK)

        except Tests.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Тест не найден']}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': ['Пользователь не найден']},
                                status=status.HTTP_400_BAD_REQUEST)
        except Answers.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Один из вопросов не найден'},
                                status=status.HTTP_400_BAD_REQUEST)


    @action(methods=['POST'], detail=False)
    def get_answers(self, request):

        serializer = GetAnswersSerializer(data=request.data)

        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = serializer.validated_data['user_id']
            test_id = serializer.validated_data['test_id']

            test = (Tests.objects.prefetch_related(
                Prefetch('test_question_test',
                         queryset=TestQuestions.objects.prefetch_related(
                             Prefetch(
                                 'answer_question',
                                 queryset=Answers.objects.all(),
                                 to_attr='_prefetched_answers'
                             )
                         ),
                         to_attr='_prefetched_questions')
            ).get(pk=test_id))

            user = User.objects.prefetch_related(
                Prefetch(
                    'observed_user',
                    queryset=Observed.objects.all(),
                    to_attr='_prefetched_observed'
                )
            ).get(pk=user_id)

            observed = user._prefetched_observed[0]

            test_result = TestResult.objects.get(test=test, observed=observed)

            tests_contex = {
                'request': request,
                'user': user,
                'observed': observed,
                'test_result': test_result,
            }

            return JsonResponse({'success': True, 'result': TestSerializer(test, context=tests_contex).data},
                                status=status.HTTP_200_OK)
        except Tests.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Тест не найден'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'errors': 'Пользователь не найден'},
                                status=status.HTTP_400_BAD_REQUEST)
