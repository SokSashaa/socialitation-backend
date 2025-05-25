from django.db.models import Prefetch

from socialize_main.models import TestQuestions, Answers


def get_questions(obj):
    questions = getattr(obj, '_prefetched_questions', None)

    if questions is None:
        try:
            questions = TestQuestions.objects.filter(test=obj).prefetch_related(
                Prefetch(
                    'answer_question',
                    queryset=Answers.objects.all(),
                    to_attr='_prefetched_answers'
                )
            )
        except TestQuestions.DoesNotExist:
            return []

    return questions
