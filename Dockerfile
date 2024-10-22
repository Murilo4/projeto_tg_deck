# Use a imagem oficial do Python como base
FROM python:3.9

# Defina o diretório de trabalho
WORKDIR /app

# Copie os arquivos de requisitos para o container
COPY requirements.txt .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Exponha a porta que o Django irá rodar
EXPOSE 8001

# Comando para rodar o servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]