from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework import exceptions
from ..serializers import PersonDeckGetSerializer, PersonDeckUpdateSerializer
from ..serializers import UserDeckSerializer, PersonDeckSerializer
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from ..models import Deck, UserDeck
import requests
from django.core.exceptions import ValidationError
from django.db.models import Q
from ..validate import validate_jwt


@csrf_exempt
@api_view(['GET'])
def get_all_decks(request):
    if request.method == 'GET':
        try:
            response = requests.post(
                f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
            if response.status_code == 404:
                raise ValidationError(f'Não foi possivel validar o token.')

            token = request.headers.get('Authorization')
            if token and token.startswith("Bearer "):
                token = token[7:]  # Remove "Bearer " do token

                # Função de validação do JWT
                jwt_data = validate_jwt(token)
                user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                    'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Busca UserStandardDeck para o usuário
            user_decks = UserDeck.objects.filter(user_id=user_id)
            standard_deck_ids = user_decks.values_list('deck_id', flat=True)

            # Busca os objetos Deck completos usando os IDs
            custom_decks = Deck.objects.filter(id__in=standard_deck_ids)

            # Serialização dos dados
            custom_decks_serializer = PersonDeckGetSerializer(
                custom_decks, many=True)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'custom_decks': custom_decks_serializer.data,
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuarios não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def get_standard_decks(request):
    if request.method == 'GET':
        try:
            # Verificar o token
            response = requests.post(
                f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
            if response.status_code == 404:
                raise ValidationError(f'Não foi possivel validar o token.')

            token = request.headers.get('Authorization')
            if token.startswith("Bearer "):
                token = token[7:]

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Obter todos os decks que estão na tabela UserDeck para o usuário atual
            user_decks = UserDeck.objects.filter(
                user_id=user_id).values_list('deck_id', flat=True)

            # Filtrar na tabela Deck os decks do tipo 'Standard' que não estão vinculados ao usuário
            standard_decks = Deck.objects.filter(
                type_deck='Standard').exclude(id__in=user_decks)

            # Serializar os decks filtrados
            standard_decks_serializer = PersonDeckSerializer(
                standard_decks, many=True)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'standard_decks': standard_decks_serializer.data
            }, status=status.HTTP_200_OK)

        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuários não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return JsonResponse({'success': False,
                                 'message': f'Erro: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['GET'])
def get_deck(request):
    if request.method == 'GET':
        deck_id = request.data.get('deckId')
        try:
            response = requests.post(
                f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
            if response.status_code == 404:
                raise ValidationError(f'Não foi possivel validar o token.')

            token = request.headers.get('Authorization')
            if token.startswith("Bearer "):
                token = token[7:]

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)

            custom_decks = Deck.objects.get(id=deck_id)
            custom_decks_serializer = PersonDeckGetSerializer(custom_decks)

            return JsonResponse({
                'success': True,
                'message': 'dados retornados',
                'custom_decks': custom_decks_serializer.data
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuarios não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['PUT'])
def deck_update(request):
    if request.method == 'PUT':
        try:
            deck_id = request.data.get('deckId')
            response = requests.post(
                f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
            if response.status_code == 404:
                raise ValidationError(f'Não foi possivel validar o token.')

            token = request.headers.get('Authorization')
            if token.startswith("Bearer "):
                token = token[7:]

            jwt_data = validate_jwt(token)
            user_id = jwt_data.get('id')

            user_deck_exists = UserDeck.objects.filter(
                user_id=user_id, deck_id=deck_id).exists()
            try:
                deck = Deck.objects.get(id=deck_id)
            except Deck.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Deck não localizado'
                }, status=status.HTTP_404_NOT_FOUND)

            if not user_deck_exists:
                return JsonResponse({"sucess": False,
                                     "message":
                                    "Você não tem permissão para modificar este deck"},
                                    status=status.HTTP_401_UNAUTHORIZED)

            if deck.type_deck == "Standard":
                return JsonResponse({"sucess": False,
                                    "message":
                                     "Você não tem permissão para modificar este deck"},
                                    status=status.HTTP_401_UNAUTHORIZED)
            user_deck = UserDeck.objects.filter(deck_id=deck_id).count() > 1
            if user_deck:
                new_deck_data = {field.name: getattr(deck, field.name) for field in Deck._meta.fields if field.name not in ['id', 'public']}

                # Altera o campo 'public'
                new_deck_data['public'] = 0
                new_deck = Deck.objects.create(**new_deck_data)

                # Desvincular o usuário do deck antigo
                UserDeck.objects.filter(
                    deck_id=deck_id, user_id=user_id).delete()

                # Associar o novo deck ao usuário
                UserDeck.objects.create(user_id=user_id, deck_id=new_deck.id)

                # Atualizar o novo deck com os dados recebidos
                serializer = PersonDeckUpdateSerializer(
                    new_deck, data=request.data, partial=True)
            else:
                # Se existir apenas um registro, atualize-o
                serializer = PersonDeckUpdateSerializer(
                    deck, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({
                    'success': True,
                    'message': 'deck atualizado'},
                    status=status.HTTP_200_OK)
            else:
                return JsonResponse({'success': False,
                                     'message':
                                     'Não foi possivel validar os dados do deck'},
                                    status=status.HTTP_400_BAD_REQUEST)
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                'message': 'Usuario não localizado'},
                                status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
def deck_delete(request):
    if request.method == 'DELETE':
        try:
            deck_id = request.data.get('deckId')
            response = requests.post(
                f'http://ec2-54-94-30-193.sa-east-1.compute.amazonaws.com:8000/validate-token/')
            if response.status_code == 404:
                raise ValidationError('Não foi possível validar o token.')

            token = request.headers.get('Authorization')
            if token and token.startswith("Bearer "):
                token = token[7:]  # Remove "Bearer " do token

                # Função de validação do JWT
                jwt_data = validate_jwt(token)
                user_id = jwt_data.get('id')

            if not user_id:
                return JsonResponse({'success': False,
                                     'message': 'userId é necessário'},
                                    status=status.HTTP_400_BAD_REQUEST)
            deck_user = UserDeck.objects.filter(deck_id=deck_id)
            if deck_user is None:
                return JsonResponse({'success': False,
                                     'message': 'Deck não encontrado para este usuário'},
                                    status=status.HTTP_404_NOT_FOUND)
            # Busca o Deck completo usando o ID
            deck = Deck.objects.filter(id=deck_id).first()
            if deck is None:
                return JsonResponse({'success': False,
                                     'message': 'Deck não encontrado para este usuário'},
                                    status=status.HTTP_404_NOT_FOUND)
            # Verificação do tipo de deck e remoção conforme necessário
            if deck.type_deck == 'Custom' and deck.public == 0:
                deck_user.delete()
                deck.delete()       # Remove do Deck
            elif deck.type_deck == 'Standard':
                # Remove apenas da tabela UserDeck
                deck_user.delete()

            # Retorna a resposta de sucesso
            return JsonResponse({
                'success': True,
                'message': 'Deck removido com sucesso.',
            })
        except exceptions.NotFound:
            return JsonResponse({'success': False,
                                 'message': 'Usuários não encontrados'},
                                status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def add_deck_to_user(request):
    deck_id = request.data.get('deckId')
    try:
        token = request.headers.get('Authorization')
        if token.startswith("Bearer "):
            token = token[7:]

        jwt_data = validate_jwt(token)
        user_id = jwt_data.get('id')
        if not deck_id:
            return JsonResponse({'success': False,
                                'message': 'Deck não encontrado.'},
                                status=status.HTTP_404_NOT_FOUND)
        if UserDeck.objects.filter(user_id=user_id, deck_id=deck_id).exists():
            return JsonResponse({"success": False,
                                 "message": "Deck já está adicionado ao usuário."},
                                status=status.HTTP_409_CONFLICT)
        standard_deck = Deck.objects.get(Q(id=deck_id) &
                                         (Q(type_deck="Standard") |
                                         Q(type_deck="Custom")) & Q(public=1))

        if standard_deck.type_deck == "Custom":
            user_standard_deck = UserDeck.objects.create(
                user_id=user_id,  # Usando o ID do usuário extraído
                deck_id=standard_deck.id
            )
            serializer = UserDeckSerializer(user_standard_deck)
            if serializer:
                return JsonResponse({'success': True,
                                     'message':
                                    'deck customizado adicionado com sucesso'},
                                    status=status.HTTP_201_CREATED)

        # Criar a instância do UserStandardDeck
        user_standard_deck = UserDeck.objects.create(
            user_id=user_id,  # Usando o ID do usuário extraído
            deck_id=standard_deck.id
        )
        serializer = UserDeckSerializer(user_standard_deck)
        if serializer:
            return JsonResponse({'success': True,
                                'message': 'deck adicionado com sucesso'},
                                status=status.HTTP_201_CREATED)
    except Deck.DoesNotExist:
        return JsonResponse({'success': False,
                             'message': 'Deck não encontrado.'},
                            status=status.HTTP_404_NOT_FOUND)
