from django.db.models import Count
from django.shortcuts import render, get_object_or_404
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView
from .forms import EmailPostForm, CommentForm
from django.core.mail import send_mail
from taggit.models import Tag

# Create your views here.

def post_list(request, tag_slug=None):
    object_list = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])
    paginator = Paginator(object_list, 3) #Trzy posty na każdej stronie
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request, 'blog/post/list.html', {
        'page': page, 
        'posts': posts,
        'tag': tag})


def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)

    #Lista aktywnych komentarzy dla danego posta
    comments = post.comments.filter(active=True)

    if request.method == 'POST':
        #Komentarz został opublikowany
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            #Utworzenie nowego komentarza, NIEZAPISAY
            new_comment = comment_form.save(commit=False)
            #Przypisanie komentarza do posta
            new_comment.post = post
            #Zapisane komentarz do bazy danych
            new_comment.save()
    else:
        comment_form = CommentForm()

    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:2]
    return render(request, 'blog/post/detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'similar_posts': similar_posts})

def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
        form = EmailPostForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{} ({}) zachęca do przeczytania "{}"'.format(cd['name'],
                                                                    cd['email'], 
                                                                    post.title)
            message = 'Przeczytaj post "{}" na stronie {}\n\n \
                       Komentarz dodany przez {}: {}'.format(
                           post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'admin@mylog.com', [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {
        'post': post,
        'form': form,
        'sent': sent
    })
    
class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'

