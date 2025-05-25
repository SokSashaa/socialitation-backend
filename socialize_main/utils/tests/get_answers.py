from socialize_main.models import Answers


def get_answers(question):
    answers = getattr(question, '_prefetched_answers', None)

    if answers is None:
        try:
            answers = Answers.objects.filter(question=question)
        except Answers.DoesNotExist:
            return []

    return answers
