from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@api_view(['GET'])
def view_test(request):
    if request.method == 'GET':
        try:
            return JsonResponse({
                "success": True,
                "message": "Usuário encontrado"},
                status=status.HTTP_200_OK)
        except:
            return JsonResponse({
                "success": False,
                "message": "Usuário não foi encontrado"},
                status=status.HTTP_404_NOT_FOUND)



