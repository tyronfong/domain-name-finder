from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.views import generic
from django.contrib.auth import authenticate, login
from django.db import IntegrityError
from .models import Word, Domain, Question, Choice
import logging, csv
import thread, whois
from django.db.models import Q
from multiprocessing.pool import ThreadPool
from socket import error as SocketError
from functools import partial

logging.basicConfig()
logger = logging.getLogger(__name__)

pool = ThreadPool(100)


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


def redo(request):
    if request.user.is_authenticated():
        try:
            thread.start_new_thread(__domain_re_calculate,
                                    (Domain.objects.filter(Q(is_checked=True) & Q(is_available=True) | Q(is_checked=False)),))
        except Exception, e:
            logger.error("Error: unable to start thread" + str(e))
        return HttpResponse("Redo triggered.")
    else:
        return HttpResponse("Pls login first.")


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
            word = Word(word=request.POST['word'].lower())
            word.save()
            #  if word save successfully, then it's a new word, can be used to calculate new domain list.
            try:
                thread.start_new_thread(__domain_calculate, (word.word,))
            except Exception, e:
                logger.error("Error: unable to start thread" + str(e))

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


def export_view(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_domain_names.csv"'

    writer = csv.writer(response)
    writer.writerow(['domain', 'isChecked', 'isAvailable'])
    for domain in Domain.objects.all():
        writer.writerow([domain.name, domain.is_checked, domain.is_available])

    return response


def __get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def __domain_calculate(word):
    new_domain_single = Domain(name=word)
    new_domain_single.save()
    for a_word in words_cache.cache:
        new_domain = Domain(name=a_word.word + word)
        new_domain_invert = Domain(name=word + a_word.word)
        new_domain.save()
        new_domain_invert.save()

    new_domains = __get_all_new_domains(word)
    pool.map(partial(__query_whois_for_single_domain, count=0), new_domains)
    words_cache.cache.append(Word(word=word))
    pass


def __domain_re_calculate(domains):
    pool.map(partial(__query_whois_for_single_domain, count=0), domains)


def __get_all_new_domains(word):
    return Domain.objects.filter(Q(name__startswith=word) | Q(name__endswith=word))


def __query_whois_for_single_domain(domain, count):
    try:
        logger.info('querying whois for domain: ' + domain.name)
        logger.info('count: ' + str(count))
        whois.whois(domain.name + ".com")
        domain.is_checked = True
        domain.is_available = False
        domain.save()
    except whois.parser.PywhoisError:
        domain.is_checked = True
        domain.is_available = True
        domain.save()
        logger.info(domain.name + '.com' + ' is available.')
    except SocketError as e:
        if count < 5:
            logger.info('retry: ' + count + ' querying whois for domain: ' + domain.name)
            __query_whois_for_single_domain(domain, count+1)
        else:
            logger.error('fail to query domain after 5 times retry' + str(e))

