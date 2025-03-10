from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from blogs.templatetags.markdownify import markdown
from blogs.models import Blog
from blogs.helpers import bulk_email
import djqscsv


@staff_member_required
def review_flow(request):
    unreviewed_blogs = Blog.objects.filter(reviewed=False, blocked=False).exclude(content='Hello World!').order_by('created_date')

    if unreviewed_blogs:
        blog = unreviewed_blogs[0]
        all_posts = blog.post_set.filter(publish=True).order_by('-published_date')

        return render(
            request,
            'review_flow.html',
            {
                'blog': blog,
                'content': blog.content or "~nothing here~",
                'posts': all_posts,
                'root': blog.useful_domain(),
                'still_to_go': len(unreviewed_blogs)
            })
    else:
        return HttpResponse("No blogs left to review! \ʕ•ᴥ•ʔ/")


@staff_member_required
def approve(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    blog.reviewed = True
    blog.save()
    if not request.GET.get("no-email", ""):
        send_mail(
            'Some blogging extras 🐻',
            f'''
Hey, welcome to your "bear" blogging experience!

I'm Herman, the creator and maintainer of Bear.

I've built Bear to be 100% free, open-source, and community centric.
If you're keen to support the project you can do that here: https://bearblog.dev/contribute/

Supporters will receive beta access to new features like email subscriptions.

Have an awesome week!

Herman
            ''',
            'Herman at Bear Blog <hi@bearblog.dev>',
            [blog.user.email]
        )
    return redirect('review_flow')


@staff_member_required
def block(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    blog.blocked = True
    blog.save()
    return redirect('review_flow')


@staff_member_required
def export_emails(request):
    users = Blog.objects.filter(reviewed=True, blocked=False).values('user__email')

    return djqscsv.render_to_csv_response(users)


@staff_member_required
def bulk_mail_users(request):
    if request.method == "POST":
        if request.POST.get("subject", "") and request.POST.get("body", ""):
            if request.POST.get("is_test", ""):
                # Sends to first registered user (assuming that's the admin)
                queryset = Blog.objects.filter(pk=1)
            else:
                queryset = Blog.objects.filter(blocked=False, reviewed=True)
            bulk_email(
                queryset,
                request.POST.get("subject", ""),
                markdown(request.POST.get("body", ""))
            )
            return HttpResponse(f"Your mail has been sent to {len(queryset)} users!")
        return render(
            request,
            'staff/bulk_mail_users.html',
            {'error': 'Missing message subject or body'}
        )
    else:
        return render(
            request,
            'staff/bulk_mail_users.html',
            {}
        )


def bulk_mail_unsubscribe(request, email):
    blog = get_object_or_404(Blog, user__email=email)
    blog.subscribed = False
    blog.save()
    return HttpResponse('You have been successfully unsubscribed.')
