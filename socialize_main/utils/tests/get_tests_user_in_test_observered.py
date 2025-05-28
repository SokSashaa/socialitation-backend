from django.db.models import Prefetch

from socialize_main.models import TestObservered, Answers, TestQuestions


def get_tests_user_in_test_observered(user_id, search=None):
    test_observers = (TestObservered.objects
    .filter(observed__user__pk=user_id)
    .select_related('test', 'observed')
    .prefetch_related(
        Prefetch('test__test_question_test',
                 queryset=TestQuestions.objects.prefetch_related(
                     Prefetch(
                         'answer_question',
                         queryset=Answers.objects.all(),
                         to_attr='_prefetched_answers'
                     )
                 ),
                 to_attr='_prefetched_questions')
    ))

    if search:
        test_observers.filter(test__title__icontains=search)

    tests = []
    for test_observer in test_observers:
        test = test_observer.test
        test._prefetched_questions = getattr(test, '_prefetched_questions', [])
        test._prefetched_test_observer = test_observer
        tests.append(test)

    return tests
