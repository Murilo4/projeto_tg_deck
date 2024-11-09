import requests
import json
from textblob import Word
from rest_framework.decorators import api_view
from django.http import JsonResponse
from reverso_api.context import ReversoContextAPI
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
@api_view(["POST"])
def get_correct_word(request):
    word = request.data.get('word')

    if not word:
        return JsonResponse({'success': False,
                             'message': 'Texto é obrigatório.'})

    try:
        blob = Word(word)
        corrected_text = str(blob.correct())
        if corrected_text == word:
            return JsonResponse({'success': True,
                                 'message': 'Nenhuma mudança necessária.'})
        else:
            corrected_text = blob.spellcheck()
            return JsonResponse({'success': True,
                                 'corrected_text': corrected_text})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Erro: {str(e)}"})


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Content-Type": "application/json; charset=UTF-8"
}


@csrf_exempt
@api_view(["POST"])
def get_correct_phrase(request):
    if request.method == 'POST':
        # Pega o texto do corpo da requisição
        phrase = request.data.get('phrase', '')

        # Se o texto não for vazio, verifique a gramática
        if phrase:
            corrected_text = correct_phrases(phrase)
            return JsonResponse({'original_text': phrase,
                                 'corrected_text': corrected_text})
        else:
            return JsonResponse({'error': 'No text provided'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=400)


def correct_phrases(phrase):
    url = "https://api.languagetool.org/v2/check"
    params = {
        'text': phrase,
        'language': 'en'
    }

    response = requests.post(url, data=params)
    result = response.json()

    # Corrigir o texto com base nas sugestões da API
    corrected_text = phrase
    for match in result.get('matches', []):
        for replacement in match['replacements']:
            # Aplicando a primeira correção sugerida
            corrected_text = corrected_text[:match['offset']] + replacement['value'] + corrected_text[match['offset'] + match['length']:]

    return corrected_text


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
                                     'message': 'A palavra é obrigatória.'})

            # Inicializa a API ReversoContextAPI
            api = ReversoContextAPI(word, "", source_lang, target_lang)

            # Realiza uma chamada para garantir que há uma resposta válida
            response = requests.post(
                "https://context.reverso.net/bst-query-service",
                headers=HEADERS,
                data=json.dumps(api._ReversoContextAPI__data))

            if response.status_code != 200:
                return JsonResponse({'success': False,
                                     'message':
                                     f"Erro na requisição: {response.status_code}"})

            try:
                translations_json = response.json().get(
                    "dictionary_entry_list", [])
            except ValueError:
                return JsonResponse({'success': False,
                                     'message':
                                     "Resposta JSON inválida ou vazia."})

            # Processa traduções se houver
            translations = []
            for translation in translations_json:
                translations.append({
                    "source_word": translation.get("term"),
                    "translation": translation.get("alignFreq")
                })
            translations = translations[:8]
            return JsonResponse({'success': True,
                                 "message": "Palavra traduzida",
                                "translations": translations})

        except Exception as e:
            return JsonResponse({'success': False,
                                 'message':
                                 f"Erro ao buscar traduções: {str(e)}"})


@api_view(['POST'])
def get_example_sentences(request):
    if request.method == 'POST':
        try:
            word = request.data.get('word')
            source_lang = request.data.get('source_lang', 'en')
            target_lang = request.data.get('target_lang', 'pt')

            if not word:
                return JsonResponse({'success': False,
                                     'message': 'A palavra é obrigatória.'})

            # Inicializa a API ReversoContextAPI
            api = ReversoContextAPI(word, "", source_lang, target_lang)

            # Realiza uma chamada para garantir que há uma resposta válida
            response = requests.post("https://context.reverso.net/bst-query-service", headers=HEADERS,
                                     data=json.dumps(
                                         api._ReversoContextAPI__data))

            if response.status_code != 200:
                return JsonResponse({'success': False,
                                     'message':
                                     f"Erro na requisição: {response.status_code}"})

            # Tenta carregar o conteúdo JSON
            try:
                # Certifique-se de acessar a chave correta
                examples_json = response.json().get("list", [])
            except ValueError:
                return JsonResponse({'success': False,
                                     'message':
                                     "Resposta JSON inválida ou vazia."})

            # Processa exemplos se houver
            examples = []
            for example in examples_json:
                examples.append({
                    "source_sentence": example.get("s_text")
                })

            if not examples:
                return JsonResponse({'success': True, 
                                     'message': "Nenhum exemplo encontrado.",
                                     "examples": []})

            # Retorno para o usuário
            return JsonResponse({'success': True,
                                 "message": "Frases de exemplo obtidas",
                                 "examples": examples})

        except Exception as e:
            print("Erro ao buscar frases:", e)
            return JsonResponse({'success': False,
                                 'message': f"Erro ao buscar frases: {str(e)}"})
