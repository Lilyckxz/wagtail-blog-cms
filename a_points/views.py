from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import PointsRecord
from django.utils.timezone import now


@login_required
def daily_check_in(request):
    # 每日签到逻辑
    user = request.user
    today = now().date()
    if PointsRecord.objects.filter(user=user, type='earn', description='Daily Check-in', created_at__date=today).exists():
        return JsonResponse({'error': 'You have already checked in today.'}, status=400)

    # 添加积分记录
    PointsRecord.objects.create(user=user, points=10, type='earn', description='Daily Check-in')
    user.profile.add_points(10)

    return JsonResponse({'success': True, 'points': user.profile.points})



@login_required
def points_records(request):
    """显示用户的积分记录"""
    records = PointsRecord.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'a_points/points_records.html', {'records': records})