from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from .models import Word, Domain, Question, Choice
import logging
import socket, thread
from django.db.models import Q
logging.basicConfig()
logger = logging.getLogger(__name__)


class WordCache:
    def __init__(self):
        pass

    cache = list(Word.objects.all())


class IndexView(generic.ListView):
    template_name = 'polls/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """Return the last five published questions."""
        return Question.objects.order_by('-pub_date')[:5]


class LoginView(generic.TemplateView):
    template_name = 'polls/login.html'


class DetailView(generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'polls/results.html'


def submit(requst, word):
    return render(requst, "polls/postWord.html")


def check(request):
    logger.info(__get_client_ip(request) + ' is trying to login system.')
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
        logger.info(__get_client_ip(request) + ' login success.')
        login(request, user)
        return render(request, 'polls/wordUpload.html')
    else:
        logger.info(__get_client_ip(request) + ' login failed.')
        return render(request, 'polls/login.html', {
            'error_msg': "username or password is incorrect."
        })

words_cache = WordCache()


def word_upload(request):
    if request.user.is_authenticated():
        try:
            word = Word(word=request.POST['word'])
            word.save()
            #  if word save successfully, then it's a new word, can be used to calculate new domain list.
            try:
                thread.start_new_thread(__domain_calculate, (request.POST['word'],))
            except Exception, e:
                logger.error("Error: unable to start thread", str(e))

        except IntegrityError:
            return render(request, 'polls/wordUpload.html', {
                'response': '"' + word.__str__() + '" is already in database. Please try another word.'
            })

        return render(request, 'polls/wordUpload.html', {
            'response': "upload success"
        })
    else:
        logger.warn('unauthenticated user is trying to upload word.')
        return render(request, 'polls/login.html')


def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        # Redisplay the question voting form.
        return render(request, 'polls/detail.html', {
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        selected_choice.votes += 1
        selected_choice.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))


def __get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def __domain_calculate(word):
    for a_word in words_cache.cache:
        new_domain = Domain(name=a_word.word+word)
        new_domain_invert = Domain(name=word+a_word.word)
        new_domain.save()
        new_domain_invert.save()

    __query_ip_for_those_domains(__get_all_new_domains(word))
    words_cache.cache.append(Word(word=word))
    pass


def __get_all_new_domains(word):
    return Domain.objects.filter(Q(name__startswith=word)|Q(name__endswith=word))


def __query_ip_for_those_domains(domains):
    for domain in domains:
        try:
            socket.gethostbyname(domain.name+".com")
            domain.is_checked = True
            domain.is_available = False
            domain.save()
        except socket.gaierror:
            domain.is_checked = True
            domain.is_available = True
            domain.save()