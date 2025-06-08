Down-Dot-You-BeUma aplicação web moderna desenvolvida com Python e Flask para criar filas de download e baixar vídeos, áudios e playlists completas do YouTube com facilidade.Key FeaturesInterface Web Intuitiva: UI limpa e moderna para adicionar URLs e gerenciar downloads.Fila de Downloads: Crie uma lista de até 10 itens para baixar em sequência.Suporte a Playlists: Detecta e baixa automaticamente todos os vídeos de uma playlist.Alta Qualidade: Baixa vídeos na melhor resolução disponível (unindo vídeo e áudio) e áudios em formato MP3 (192kbps).Organização Automática: Salva os arquivos em diretórios separados para vídeos e áudios.Logging Estruturado: Mantém um registro detalhado de todas as operações em um arquivo .csv.Technologies UsedBackend: Python 3.11+, FlaskFrontend: HTML5, Tailwind CSSCore Logic: yt-dlpDependências Adicionais: ffmpeg (para processamento de mídia)Project Structuredown-dot-you-be/
│
├── downloads/                # Pasta onde os arquivos são salvos
│   ├── videos/
│   └── audios/
│
├── logs/                     # Registros de operações
│   └── master_log.csv
│
├── static/                   # Arquivos estáticos (CSS, JS, Imagens)
│   └── images/
│       ├── 1_icon.png
│       └── video_icon.png
│       └── ...
│
├── templates/                # Arquivos HTML do Flask
│   └── index.html
│
├── .gitignore                # Arquivos e pastas a serem ignorados pelo Git
├── app.py                    # Lógica principal da aplicação Flask
├── README.md                 # Este arquivo
└── requirements.txt          # Dependências do projeto Python
Getting StartedSiga os passos abaixo para executar o projeto localmente.1. PrerequisitesPython 3.10 ou superiorGitFFmpeg (essencial para unir vídeo/áudio e para conversão para MP3). A forma mais fácil de instalar no Windows é com Chocolatey:choco install ffmpeg
2. InstallationClone o repositório:git clone https://github.com/seu-usuario/down-dot-you-be.git
cd down-dot-you-be
Crie e ative um ambiente virtual:# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
Instale as dependências:pip install -r requirements.txt
3. Running the ApplicationInicie o servidor Flask:flask run
Abra seu navegador e acesse: http://127.0.0.1:5000How to UseCole a URL de um vídeo ou playlist do YouTube no campo de URL.Selecione o tipo de download (Vídeo ou Áudio).Clique no botão "Adicionar à Fila".Repita o processo para adicionar até 10 itens.Quando sua fila estiver pronta, clique em "Iniciar Downloads".Para apagar a lista, clique em "Limpar Fila".LicenseEste projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.