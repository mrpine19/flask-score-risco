# Guia de Deploy - API Score de Risco CareLink

Este guia descreve o passo a passo para fazer o deploy da API Flask em um ambiente de produção.

## 1. Pré-requisitos

*   Servidor (Linux/Ubuntu é recomendado) com Python 3.9+ instalado.
*   Acesso ao terminal do servidor.

## 2. Passos para o Deploy

### Passo 2.1: Copiar Arquivos para o Servidor

Copie os seguintes arquivos do seu projeto para um diretório no servidor (ex: `/home/ubuntu/carelink-api`):

*   `app.py`
*   `model_carelink_v5.joblib`
*   `requirements.txt`

### Passo 2.2: Criar um Ambiente Virtual

No servidor, navegue até o diretório do projeto e crie um ambiente virtual para isolar as dependências.

```bash
cd /home/ubuntu/carelink-api
python3 -m venv venv
source venv/bin/activate
```

### Passo 2.3: Instalar as Dependências

Com o ambiente virtual ativado, instale todas as bibliotecas necessárias usando o arquivo `requirements.txt`.

```bash
pip install -r requirements.txt
```

### Passo 2.4: Testar a Aplicação com Gunicorn

O servidor de desenvolvimento do Flask (`app.run()`) não é seguro ou performático para produção. Usaremos o Gunicorn como nosso servidor WSGI.

Execute o seguinte comando para iniciar a aplicação com o Gunicorn:

```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

*   `--bind 0.0.0.0:5000`: Faz a aplicação escutar em todas as interfaces de rede na porta 5000.
*   `app:app`: Diz ao Gunicorn para encontrar a instância da aplicação Flask (a variável `app`) dentro do arquivo `app.py`.

Acesse `http://<IP_DO_SEU_SERVIDOR>:5000` em um navegador. Você verá um erro "Method Not Allowed", o que é esperado, pois a rota `/predict_risk` só aceita requisições POST. Isso confirma que o servidor está no ar.

### Passo 2.5: (Opcional, mas Recomendado) Criar um Serviço com Systemd

Para garantir que sua API inicie automaticamente com o servidor e reinicie em caso de falhas, é uma boa prática criar um serviço `systemd`.

1.  Crie um arquivo de serviço:
    ```bash
    sudo nano /etc/systemd/system/carelink.service
    ```

2.  Cole o seguinte conteúdo no arquivo. **Lembre-se de substituir `<SEU_USUARIO>` pelo seu nome de usuário no servidor (ex: `ubuntu`)**:

    ```ini
    [Unit]
    Description=Gunicorn instance to serve CareLink API
    After=network.target

    [Service]
    User=<SEU_USUARIO>
    Group=www-data
    WorkingDirectory=/home/ubuntu/carelink-api
    Environment="PATH=/home/ubuntu/carelink-api/venv/bin"
    ExecStart=/home/ubuntu/carelink-api/venv/bin/gunicorn --workers 3 --bind unix:carelink.sock -m 007 app:app

    [Install]
    WantedBy=multi-user.target
    ```

3.  Inicie e habilite o serviço:
    ```bash
    sudo systemctl start carelink
    sudo systemctl enable carelink
    ```

    Agora sua API está rodando como um serviço em background.

## 3. (Opcional) Usando Docker para Deploy

Como alternativa, você pode "containerizar" sua aplicação com o Docker, o que simplifica o deploy em qualquer ambiente que tenha o Docker instalado.

### Passo 3.1: Criar um Dockerfile

Crie um arquivo chamado `Dockerfile` (sem extensão) na raiz do seu projeto com o seguinte conteúdo:

```dockerfile
# Usar uma imagem base oficial do Python
FROM python:3.9-slim

# Definir o diretório de trabalho no container
WORKDIR /app

# Copiar o arquivo de dependências
COPY requirements.txt .

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto dos arquivos da aplicação
COPY . .

# Expor a porta que a aplicação vai rodar
EXPOSE 5000

# Comando para rodar a aplicação com Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

### Passo 3.2: Construir e Rodar o Container

1.  **Construa a imagem Docker:**
    ```bash
    docker build -t carelink-api .
    ```

2.  **Rode o container:**
    ```bash
    docker run -p 5000:5000 carelink-api
    ```

Sua API agora está rodando dentro de um container Docker e acessível na porta 5000 do seu host.
