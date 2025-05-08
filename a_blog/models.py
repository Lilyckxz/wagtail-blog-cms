from django.db import models
from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel
from wagtail.search import index
from taggit.models import TaggedItemBase
from modelcluster.fields import ParentalKey
from modelcluster.contrib.taggit import ClusterTaggableManager
from datetime import date
from django.shortcuts import redirect
from django.http import JsonResponse, HttpResponseForbidden
from taggit.models import Tag
from django.template.response import TemplateResponse  # 确保引入 TemplateResponse


class BlogPage(Page):
    body = RichTextField(blank=True)
    # body = RichTextField(
    #     blank=True,
    #     features=[  # 必须手动启用需要的格式
    #         'h2', 'h3',
    #         'bold', 'italic',
    #         'ol', 'ul',  # 允许有序/无序列表
    #         'link', 'image'
    #     ]
    # )
    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]
    
    template = "a_blog/blog_page.html"
    
    def get_context(self, request): 
        tag = request.GET.get("tag")
        if tag:
            articles = ArticlePage.objects.filter(tags__name=tag).live().order_by('-first_published_at')
        else:     
            articles = self.get_children().live().order_by('-first_published_at')
            
        # 获取所有标签
        all_tags = Tag.objects.all()
        context = super().get_context(request)
        context['articles'] = articles
        context["tag"] = tag
        context['all_tags'] = all_tags  # 将所有标签传递到模板
        return context
    
    
class ArticlePage(Page):
    intro = models.CharField(max_length=80)
    body = RichTextField(blank=True)
    date = models.DateField("Post date", default=date.today)
    image = models.ForeignKey(
        'wagtailimages.Image', on_delete=models.SET_NULL, null=True, related_name='+'
    )
    caption = models.CharField(blank=True, max_length=80)
    
    tags = ClusterTaggableManager(through='ArticleTag', blank=True)
    
    views = models.PositiveIntegerField(default=0, editable=False)

    is_free = models.BooleanField(default=True, verbose_name="是否为免费页面")
    required_points = models.PositiveIntegerField(default=0, verbose_name="所需积分")
    
    def increment_view_count(self):
        self.views += 1
        self.save(update_fields=["views"])
        
    # def serve(self, request):
    #     session_key = f'article_viewed_{self.pk}'
    #     if not request.session.get(session_key, False):
    #         self.increment_view_count()
    #         request.session[session_key] = True
    #     return super().serve(request)
    
    def image_url(self):
        return self.image.get_rendition('fill-1200x675|jpegquality-80').url
    # def image_url(self):
    #     if self.image:
    #         try:
    #             return self.image.get_rendition('fill-1200x675|jpegquality-80').url
    #         except Exception as e:
    #             print(f"Error generating rendition: {e}")
    #             return None
    #     else:
    #         print("No image found for this article.")
    #         return None
    
    def get_context(self, request):
        context = super().get_context(request)
        context["image_url"] = self.image_url()
        return context
    
    def get_tags(self):
        return ", ".join(tag.name for tag in self.tags.all())
    
    def get_author(self):
        return self.owner.profile.name
    
    def get_author_username(self):
        return self.owner.username
    
    ### 订阅用户/积分购买该页面才能查看文章，87-116行代码是新添加的，目的是在用户未订阅时重定向到订阅页面


    def serve(self, request):
        profile = request.user.profile if request.user.is_authenticated else None

        # 免费页面：所有用户都可以访问
        if self.is_free:
            return super().serve(request)

        # 会员用户可以免费访问
        if profile and profile.has_valid_subscription():
            return super().serve(request)

        # 检查是否已支付积分
        if request.session.get(f"article_access_{self.pk}", False):
            return super().serve(request)

        # 非会员用户需要消耗积分
        if profile and profile.points >= self.required_points:
            if request.method == "POST":  # 用户确认扣除积分
                profile.deduct_points(self.required_points,description="购买文章")
                request.session[f"article_access_{self.pk}"] = True  # 标记已支付
                return super().serve(request)
            else:  # 显示预览页面
                context = self.get_context(request)
                context["show_preview"] = True
                context["points_required"] = self.required_points
                return TemplateResponse(request, self.get_template(request), context)

        # 积分不足，提示充值或成为会员
        context = self.get_context(request)
        context["show_preview"] = True
        context["points_required"] = self.required_points
        context["insufficient_points"] = True
        return TemplateResponse(request, self.get_template(request), context)
    
    search_fields = Page.search_fields + [
            index.SearchField('intro'),
            index.SearchField('body'),
            index.SearchField('get_tags'),
            index.SearchField('get_author'),
            index.SearchField('get_author_username')
        ]
    
    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('image'),
        FieldPanel('caption'),
        FieldPanel('body'),
        FieldPanel('date'),
        FieldPanel('tags'),
        FieldPanel('is_free'),
        FieldPanel('required_points'),
    ]
    
class ArticleTag(TaggedItemBase):
    content_object = ParentalKey(ArticlePage, on_delete=models.CASCADE, related_name='tagged_items')  
