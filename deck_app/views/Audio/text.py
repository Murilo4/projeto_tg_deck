import requests
import json
from textblob import Word
from rest_framework.decorators import api_view
from django.http import JsonResponse
from reverso_api.context import ReversoContextAPI
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
import os


@csrf_exempt
@api_view(["POST"])
def get_correct_word(request):
    word = request.data.get('word')

    if not word:
        return JsonResponse({'success': False,
                             'error': ['Texto é obrigatório.']},
                            status=status.HTTP_404_NOT_FOUND)

    try:
        blob = Word(word)
        corrected_text = str(blob.correct())
        if corrected_text == word:
            return JsonResponse({'success': True,
                                 'message': ['Nenhuma mudança necessária.']},
                                status=status.HTTP_200_OK)
        else:
            corrected_text = blob.spellcheck()
            return JsonResponse({'success': True,
                                 'message': ["correções sugeridas"],
                                 'correctedText': corrected_text},
                                status=status.HTTP_200_OK)
    except Exception as e:
        return JsonResponse({'success': False,
                             'error': f"Erro: {str(e)}"},
                            status=status.HTTP_404_NOT_FOUND)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Content-Type": "application/json; charset=UTF-8"
}


# @csrf_exempt
# @api_view(["POST"])
# def get_correct_phrase(request):
#     if request.method == 'POST':
#         # Pega o texto do corpo da requisição
#         phrase = request.data.get('phrase', '')

#         # Se o texto não for vazio, verifique a gramática
#         if phrase:
#             corrected_text = correct_phrases(phrase)
#             return JsonResponse({'original_text': phrase,
#                                  'corrected_text': corrected_text})
#         else:
#             return JsonResponse({'success': False,
#                                 'error': 'Nenhum texto fornecido'},
#                                 status=status.HTTP_400_BAD_REQUEST)

#     return JsonResponse({'success': False,
#                         'error': 'Método invalido'},
#                         status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@api_view(["POST"])
def get_correct_phrase(request):
    phrase = request.data.get("phrase")
    if not phrase:
        return JsonResponse({"success": False,
                             "error": ["Frase não fornecida"]},
                            status=status.HTTP_400_BAD_REQUEST)

    try:
        response = requests.post(
            "https://api.sapling.ai/api/v1/edits",
            json={
                "key": "9YR0ZM15E19MER4REN6IUNT2JUJYZ9DL",
                "text": phrase,
                "session_id": "test_session",
                "language": "en",
            }
        )
        if response.status_code != 200:
            return JsonResponse({"success": False, 
                                 "error": [f"Erro {response.status_code}: {response.text}"]},
                                status=response.status_code)

        try:
            resp_json = response.json()
        except ValueError:
            return JsonResponse({"success": False,
                                 "error": ["Resposta não é um JSON válido"],
                                "response": response.text},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if "edits" in resp_json and resp_json["edits"]:
            edits = [{"replacement": edit["replacement"], "sentence": edit["sentence"]} for edit in resp_json["edits"]]
            return JsonResponse({"success": True,
                                 "message": ["Frase corrigida com sucesso"],
                                 "corrections": edits},
                                status=status.HTTP_200_OK)
        else:
            return JsonResponse({"success": True,
                                 "message": ["Sem erros encontrados."]},
                                status=status.HTTP_200_OK)

    except Exception as e:
        return JsonResponse({"success": False,
                             "error": [str(e)]},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
def get_translated_word(request):
    if request.method == 'POST':
        try:
            word = request.data.get('word')
            source_lang = request.data.get('source_lang', 'en')
            target_lang = request.data.get('target_lang', 'pt')

            if not word:
                return JsonResponse({'success': False,
                                     'error': ['A palavra é obrigatória.']},
                                    status=status.HTTP_404_NOT_FOUND)

            # Inicializa a API ReversoContextAPI
            api = ReversoContextAPI(word, "", source_lang, target_lang)

            # Realiza uma chamada para garantir que há uma resposta válida
            response = requests.post(
                "https://context.reverso.net/bst-query-service",
                headers=HEADERS,
                data=json.dumps(api._ReversoContextAPI__data))

            if response.status_code != 200:
                return JsonResponse({'success': False,
                                     'error':
                                     [f"Erro na requisição: {response.status_code}"]},
                                    status=status.HTTP_404_NOT_FOUND)

            try:
                translations_json = response.json().get(
                    "dictionary_entry_list", [])
            except ValueError:
                return JsonResponse({'success': False,
                                     'error':
                                     ["Resposta JSON inválida ou vazia."]},
                                    status=status.HTTP_404_NOT_FOUND)

            # Processa traduções se houver
            translations = []
            for translation in translations_json:
                translations.append({
                    "sourceWord": translation.get("term"),
                    "translation": translation.get("alignFreq")
                })
            translations = translations[:8]
            return JsonResponse({'success': True,
                                 "message": ["Palavra traduzida"],
                                "translations": translations},
                                status=status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse({'success': False,
                                 'error':
                                 [f"Erro ao buscar traduções: {str(e)}"]},
                                status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def get_example_sentences(request):
    if request.method == 'POST':
        try:
            word = request.data.get('word')
            source_lang = request.data.get('source_lang', 'en')
            target_lang = request.data.get('target_lang', 'pt')

            if not word:
                return JsonResponse({'success': False,
                                     'error': 'A palavra é obrigatória.'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Inicializa a API ReversoContextAPI
            api = ReversoContextAPI(word, "", source_lang, target_lang)

            # Realiza uma chamada para garantir que há uma resposta válida
            response = requests.post("https://context.reverso.net/bst-query-service", headers=HEADERS,
                                     data=json.dumps(
                                         api._ReversoContextAPI__data))

            if response.status_code != 200:
                return JsonResponse({'success': False,
                                     'error':
                                     f"Erro na requisição: {response.status_code}"},
                                    status=status.HTTP_404_NOT_FOUND)

            # Tenta carregar o conteúdo JSON
            try:
                # Certifique-se de acessar a chave correta
                examples_json = response.json().get("list", [])
            except ValueError:
                return JsonResponse({'success': False,
                                     'error':
                                     "Resposta JSON inválida ou vazia."},
                                    status=status.HTTP_404_NOT_FOUND)

            # Processa exemplos se houver
            examples = []
            for example in examples_json:
                examples.append({
                    "sourceSentence": example.get("s_text")
                })

            if not examples:
                return JsonResponse({'success': False,
                                     'message': "Nenhum exemplo encontrado.",
                                     "examples": []})

            # Retorno para o usuário
            return JsonResponse({'success': True,
                                 "message": "Frases de exemplo obtidas",
                                 "examples": examples})

        except Exception as e:
            return JsonResponse({'success': False,
                                 'error': f"Erro ao buscar frases: {str(e)}"},
                                status=status.HTTP_404_NOT_FOUND)
