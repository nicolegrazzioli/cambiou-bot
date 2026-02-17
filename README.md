# 🤖 Cambiou-Bot: Monitor de Câmbio em Tempo Real

Este projeto é um agente inteligente de monitoramento de taxas de câmbio (USD/BRL e EUR/BRL) focado em eficiência e resiliência. Ele verifica as cotações a cada 30 minutos, compara com a última execução e envia notificações automáticas via Telegram caso haja mudança nos valores.

---

## 🚀 Principais Funcionalidades

- **Monitoramento Duplo**: Acompanha cotações de Dólar (USD) e Euro (EUR) em relação ao Real (BRL).
- **Resiliência de API**: Sistema de **Dual-API** que tenta obter dados da AwesomeAPI e, em caso de falha (como erro 429 de limite de requisições), utiliza a `open.er-api.com` como fallback.
- **Lógica de Notificação Inteligente**: Só envia mensagens se houver alteração no preço, indicando a tendência (📈 SUBIU ou 📉 CAIU).
- **Simulação Wise**: Calcula automaticamente o valor aproximado para remessas (Taxa + 2%).
- **Automação Total**: Executado via GitHub Actions sem necessidade de servidor próprio.
- **Persistência de Estado**: Salva o histórico da última execução no próprio repositório (`last_run.json`).

---

## 🛠️ Stack Tecnológica

- **Linguagem**: Python 3.9+
- **Bibliotecas**: `requests` para chamadas de API.
- **Automação**: GitHub Actions.
- **Notificações**: Telegram Bot API.

---

## 📋 Arquitetura e Funcionamento

### 1. Script Principal (`main.py`)
O núcleo do bot segue este fluxo:
1.  **Requisição com Retry**: Tenta acessar a API primária com um algoritmo de *exponential backoff* (espera tempos crescentes em caso de erro).
2.  **Fallback**: Se a API primária falhar após 3 tentativas, aciona a API secundária.
3.  **Comparação**: Lê o arquivo `last_run.json` para obter a cotação da execução anterior.
4.  **Cálculo**: Se o preço mudou, calcula o "Preço Wise" (Cotação + 2%).
5.  **Notificação**: Formata uma mensagem em Markdown e envia para o chat configurado.
6.  **Atualização**: Sobrescreve o `last_run.json` com os novos valores para a próxima comparação.

### 2. Automação (`scheduler.yml`)
O workflow do GitHub Actions:
- **Agendamento**: Roda a cada 30 minutos (`*/30 * * * *`).
- **Segurança**: Utiliza segredos do GitHub para esconder o Token do Bot e o ID do Chat.
- **Sincronização**: Se houver mudança de preço, o bot realiza um `git commit` e `git push` automático do arquivo de estado, utilizando `rebase` para evitar conflitos de merge.

---

## ⚙️ Configuração

### Pré-requisitos
1.  Um **Bot no Telegram** (criado via [@BotFather](https://t.me/botfather)).
2.  O seu **Chat ID** (pode ser obtido via [@userinfobot](https://t.me/userinfobot)).

### Configuração no GitHub
No seu repositório, vá em `Settings > Secrets and variables > Actions` e adicione:
- `TELEGRAM_TOKEN`: O token fornecido pelo BotFather.
- `TELEGRAM_CHAT_ID`: O ID do seu chat ou grupo.

### Rodando Localmente
```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente (ou criar um arquivo .env)
export TELEGRAM_TOKEN="seu_token"
export TELEGRAM_CHAT_ID="seu_id"

# Executar
python main.py
```

---

## 📝 Exemplo de Notificação

> **[USD] CAIU 📉 para R$ 5.72.**  
> **Wise: R$ 5.83**

---

## 📄 Licença
Este projeto está sob a licença MIT. Sinta-se à vontade para usar e modificar.