import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configurações
TOKEN = "8054308091:AAFc27gqOIUp4Oj1WhAgVS5AekBtVlhYX1s"
ADMIN_ID = 7722803509
PRODUTOS_FILE = "produtos.json"
BACKUP_FOLDER = "backups"
CHAVE_PIX = "47717a5f-3ec6-49b9-957f-31e106aa5176"
BANNER_URL = "https://i.imgur.com/yourbanner.jpg"  # Substitua por um banner profissional

# Estados da conversa
(
    AGUARDANDO_NOME,
    AGUARDANDO_DESCRICAO,
    AGUARDANDO_PRECO,
    AGUARDANDO_FOTO,
    AGUARDANDO_LINK,
    AGUARDANDO_PREVIA,
) = range(6)

# Emojis para melhorar a interface
EMOJIS = {
    "id": "🆔",
    "nome": "📛",
    "descricao": "📝",
    "preco": "💰",
    "foto": "🖼️",
    "link": "🔗",
    "previa": "👀",
    "admin": "👑",
    "produto": "🛍️",
    "sucesso": "✅",
    "erro": "❌",
    "pix": "💸",
    "comprovante": "🧾",
    "ban": "🚫",
    "warning": "⚠️",
}

# Criar a pasta de backup, se não existir
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

class DatabaseManager:
    @staticmethod
    def carregar_dados(arquivo):
        """Carrega dados de um arquivo JSON"""
        if os.path.exists(arquivo):
            try:
                with open(arquivo, "r", encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}

    @staticmethod
    def salvar_dados(arquivo, dados):
        """Salva dados em um arquivo JSON e cria backup"""
        with open(arquivo, "w", encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        
        # Criar backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_FOLDER, f"{os.path.basename(arquivo)}_{timestamp}.json")
        with open(backup_file, "w", encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)

    @classmethod
    def carregar_produtos(cls):
        """Carrega produtos garantindo que todos os campos existam"""
        produtos = cls.carregar_dados(PRODUTOS_FILE)
        
        # Garantir que todos os produtos tenham todos os campos
        for produto_id, produto_info in produtos.items():
            produto_info.setdefault('link', "")
            produto_info.setdefault('previa', "")
            produto_info.setdefault('foto_id', "")
            
        return produtos

    @classmethod
    def salvar_produtos(cls, produtos):
        """Salva os produtos no arquivo"""
        cls.salvar_dados(PRODUTOS_FILE, produtos)

# ========== HANDLERS PRINCIPAIS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para o comando /start"""
    user = update.effective_user
    welcome_message = (
        f"👋 Olá, {user.first_name}!\n\n"
        f"Bem-vindo ao *VIP Content Store* - Sua loja de conteúdos exclusivos!\n\n"
        "🔹 Acesse produtos exclusivos\n"
        "🔹 Conteúdos premium\n"
        "🔹 Entrega instantânea após pagamento\n\n"
        "Use /produtos para ver nossa seleção VIP 👑"
    )
    
    # Se tivermos um banner, enviamos com a mensagem
    try:
        await update.message.reply_photo(
            photo=BANNER_URL,
            caption=welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
    except:
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )

async def produtos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para listar todos os produtos"""
    produtos = DatabaseManager.carregar_produtos()
    
    if not produtos:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Nenhum produto disponível no momento. Volte mais tarde!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Enviar cada produto como uma mensagem separada
    for produto_id, produto_info in produtos.items():
        mensagem = (
            f"{EMOJIS['produto']} *{produto_info['nome']}* {EMOJIS['produto']}\n\n"
            f"{EMOJIS['id']} *ID:* `{produto_id}`\n"
            f"{EMOJIS['descricao']} *Descrição:*\n{produto_info['descricao']}\n\n"
            f"{EMOJIS['preco']} *Preço:* R$ {produto_info['preco']:.2f}\n"
        )

        keyboard = [
            [InlineKeyboardButton(
                f"{EMOJIS['pix']} COMPRAR AGORA {EMOJIS['pix']}", 
                callback_data=f"comprar_{produto_id}"
            )],
            [InlineKeyboardButton(
                f"{EMOJIS['previa']} Ver Prévia", 
                callback_data=f"previa_{produto_id}"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Se houver foto, envie com foto, senão envie apenas texto
        if produto_info.get('foto_id'):
            try:
                await update.message.reply_photo(
                    photo=produto_info['foto_id'],
                    caption=mensagem,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Erro ao enviar foto: {e}")
                await update.message.reply_text(
                    mensagem,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
        else:
            await update.message.reply_text(
                mensagem,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )

# ========== HANDLERS DE COMPRA ==========
async def comprar_produto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para iniciar o processo de compra"""
    query = update.callback_query
    await query.answer()
    
    produto_id = query.data.split("_")[1]
    produtos = DatabaseManager.carregar_produtos()
    
    if produto_id in produtos:
        produto = produtos[produto_id]
        
        mensagem = (
            f"🛒 *Confirmar Compra* 🛒\n\n"
            f"{EMOJIS['produto']} *Produto:* {produto['nome']}\n"
            f"{EMOJIS['preco']} *Valor:* R$ {produto['preco']:.2f}\n\n"
            f"{EMOJIS['pix']} *Pagamento via PIX* {EMOJIS['pix']}\n"
            f"Chave PIX (Copie e cole):\n\n"
            f"`{CHAVE_PIX}`\n\n"
            f"⚠️ *ATENÇÃO:* Envie o comprovante aqui mesmo após o pagamento para liberarmos seu acesso."
        )
        
        # Editar a mensagem original para mostrar os detalhes da compra
        if query.message.photo:
            await query.edit_message_caption(
                caption=mensagem, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=None
            )
        else:
            await query.edit_message_text(
                text=mensagem, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=None
            )

        # Armazenar informações do usuário para processar o comprovante
        context.user_data['aguardando_comprovante'] = True
        context.user_data['produto_id'] = produto_id
        context.user_data['user_id'] = query.from_user.id
        context.user_data['username'] = query.from_user.username or "Sem username"
    else:
        await query.answer("Produto não encontrado.", show_alert=True)

async def ver_previa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para mostrar a prévia do produto"""
    query = update.callback_query
    await query.answer()
    
    produto_id = query.data.split("_")[1]
    produtos = DatabaseManager.carregar_produtos()
    
    if produto_id in produtos and produtos[produto_id]['previa']:
        link_previa = produtos[produto_id]['previa']
        mensagem = (
            f"🔍 *Prévia do Produto* 🔍\n\n"
            f"Você está visualizando uma amostra do conteúdo:\n\n"
            f"👉 [Clique aqui para acessar a prévia]({link_previa})"
        )
        
        await query.message.reply_text(
            text=mensagem, 
            parse_mode=ParseMode.MARKDOWN, 
            disable_web_page_preview=False
        )
    else:
        await query.answer(
            "Este produto não possui prévia disponível ou seu dispositivo não suporta o formato.",
            show_alert=True
        )

async def processar_comprovante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para processar comprovantes de pagamento"""
    if not context.user_data.get('aguardando_comprovante'):
        return

    produto_id = context.user_data.get('produto_id')
    user_id = context.user_data.get('user_id')
    username = context.user_data.get('username', "Sem username")
    
    produtos = DatabaseManager.carregar_produtos()
    produto = produtos.get(produto_id, {})
    
    if update.message.photo or update.message.document:
        # Mensagem para o administrador
        mensagem_admin = (
            f"📄 *Novo Comprovante Recebido* 📄\n\n"
            f"👤 *Usuário:* @{username} (ID: {user_id})\n"
            f"🛒 *Produto:* {produto.get('nome', 'N/A')}\n"
            f"💰 *Valor:* R$ {produto.get('preco', '0.00'):.2f}\n"
            f"🆔 *ID do Produto:* {produto_id}"
        )

        # Enviar o comprovante para o admin
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID, 
                photo=update.message.photo[-1].file_id, 
                caption=mensagem_admin,
                parse_mode=ParseMode.MARKDOWN
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID, 
                document=update.message.document.file_id, 
                caption=mensagem_admin,
                parse_mode=ParseMode.MARKDOWN
            )

        # Botões de ação para o admin
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{EMOJIS['sucesso']} Liberar Acesso", 
                    callback_data=f"liberar_{user_id}_{produto_id}"
                ),
                InlineKeyboardButton(
                    f"{EMOJIS['erro']} Rejeitar", 
                    callback_data=f"rejeitar_{user_id}"
                )
            ]
        ]
        
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text="Selecione uma ação:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Confirmar recebimento para o usuário
        await update.message.reply_text(
            f"{EMOJIS['sucesso']} *Comprovante recebido!*\n\n"
            "Estamos verificando seu pagamento. Você receberá uma mensagem assim que seu acesso for liberado.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Limpar o estado de espera
        context.user_data.pop('aguardando_comprovante', None)
    else:
        await update.message.reply_text(
            f"{EMOJIS['erro']} Por favor, envie uma foto ou documento do comprovante.",
            parse_mode=ParseMode.MARKDOWN
        )

async def liberar_acesso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para liberar acesso ao produto após pagamento confirmado"""
    query = update.callback_query
    await query.answer()
    
    _, user_id, produto_id = query.data.split("_")
    user_id = int(user_id)
    
    produtos = DatabaseManager.carregar_produtos()
    produto = produtos.get(produto_id, {})
    
    if produto.get('link'):
        mensagem_usuario = (
            f"🎉 *Pagamento Confirmado!* 🎉\n\n"
            f"Seu acesso ao produto *{produto['nome']}* foi liberado!\n\n"
            f"👉 [Clique aqui para acessar seu conteúdo]({produto['link']})\n\n"
            f"Obrigado por sua compra! Se tiver qualquer dúvida, entre em contato."
        )
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=mensagem_usuario,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            
            mensagem_admin = (
                f"{EMOJIS['sucesso']} *Acesso liberado com sucesso!*\n\n"
                f"👤 Usuário: {user_id}\n"
                f"📦 Produto: {produto['nome']}\n"
                f"💵 Valor: R$ {produto['preco']:.2f}"
            )
            
            await query.edit_message_text(
                text=mensagem_admin,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para o usuário: {e}")
            await query.edit_message_text(
                text=f"{EMOJIS['erro']} Erro ao enviar mensagem para o usuário. Ele pode ter bloqueado o bot.",
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await query.edit_message_text(
            text=f"{EMOJIS['erro']} Erro: Link do produto não encontrado.",
            parse_mode=ParseMode.MARKDOWN
        )

async def rejeitar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para rejeitar um pagamento"""
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split("_")[1])
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"{EMOJIS['erro']} *Seu comprovante foi rejeitado.*\n\n"
                "Por favor, verifique se:\n"
                "1. O valor está correto\n"
                "2. O comprovante é legível\n"
                "3. O pagamento foi realmente realizado\n\n"
                "Entre em contato com nosso suporte para mais informações."
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        
        await query.edit_message_text(
            text=f"{EMOJIS['sucesso']} Comprovante rejeitado e usuário notificado.",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem de rejeição: {e}")
        await query.edit_message_text(
            text=f"{EMOJIS['erro']} Comprovante rejeitado, mas não foi possível notificar o usuário.",
            parse_mode=ParseMode.MARKDOWN
        )

# ========== ADMIN HANDLERS ==========
async def adicionar_produto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o processo de adição de produto (admin only)"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text(
            f"{EMOJIS['erro']} Você não tem permissão para usar este comando.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"{EMOJIS['admin']} *Modo Administrador - Adicionar Produto*\n\n"
        "Por favor, envie o nome do produto:",
        parse_mode=ParseMode.MARKDOWN
    )
    return AGUARDANDO_NOME

async def receber_nome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o nome do novo produto"""
    context.user_data['nome'] = update.message.text
    await update.message.reply_text(
        "Ótimo! Agora envie a descrição do produto:",
        parse_mode=ParseMode.MARKDOWN
    )
    return AGUARDANDO_DESCRICAO

async def receber_descricao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a descrição do novo produto"""
    context.user_data['descricao'] = update.message.text
    await update.message.reply_text(
        "Agora, envie o preço do produto (apenas números, ex: 49.99):",
        parse_mode=ParseMode.MARKDOWN
    )
    return AGUARDANDO_PRECO

async def receber_preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o preço do novo produto"""
    try:
        preco = float(update.message.text.replace(",", "."))
        if preco <= 0:
            raise ValueError
        context.user_data['preco'] = preco
        await update.message.reply_text(
            "Agora, envie a foto do produto:",
            parse_mode=ParseMode.MARKDOWN
        )
        return AGUARDANDO_FOTO
    except (ValueError, TypeError):
        await update.message.reply_text(
            f"{EMOJIS['erro']} Preço inválido. Envie um número positivo (ex: 49.99 ou 50).",
            parse_mode=ParseMode.MARKDOWN
        )
        return AGUARDANDO_PRECO

async def receber_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe a foto do novo produto"""
    if update.message.photo:
        context.user_data['foto_id'] = update.message.photo[-1].file_id
        await update.message.reply_text(
            "Agora, envie o link que será liberado após o pagamento:",
            parse_mode=ParseMode.MARKDOWN
        )
        return AGUARDANDO_LINK
    
    await update.message.reply_text(
        f"{EMOJIS['erro']} Por favor, envie uma foto válida.",
        parse_mode=ParseMode.MARKDOWN
    )
    return AGUARDANDO_FOTO

async def receber_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o link do produto"""
    link = update.message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        await update.message.reply_text(
            f"{EMOJIS['erro']} Link inválido. Deve começar com http:// ou https://",
            parse_mode=ParseMode.MARKDOWN
        )
        return AGUARDANDO_LINK
    
    context.user_data['link'] = link
    await update.message.reply_text(
        "Deseja adicionar um link de prévia? (Envie o link ou 'não' para pular):",
        parse_mode=ParseMode.MARKDOWN
    )
    return AGUARDANDO_PREVIA

async def receber_previa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o link de prévia do produto"""
    resposta = update.message.text.strip().lower()
    
    if resposta != 'não' and resposta != 'nao':
        if resposta.startswith("http://") or resposta.startswith("https://"):
            context.user_data['previa'] = resposta
        else:
            await update.message.reply_text(
                f"{EMOJIS['erro']} Link inválido. Pulando a prévia.",
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data['previa'] = ""
    else:
        context.user_data['previa'] = ""
    
    # Salvar o produto
    produtos = DatabaseManager.carregar_produtos()
    
    # Gerar novo ID de forma segura
    try:
        ids_existentes = [int(k) for k in produtos.keys()] if produtos else [0]
        novo_id = str(max(ids_existentes) + 1)
    except (ValueError, KeyError) as e:
        logger.error(f"Erro ao gerar novo ID: {e}")
        novo_id = "1"
    
    produtos[novo_id] = {
        "nome": context.user_data['nome'],
        "descricao": context.user_data['descricao'],
        "preco": context.user_data['preco'],
        "foto_id": context.user_data['foto_id'],
        "link": context.user_data['link'],
        "previa": context.user_data.get('previa', "")
    }
    
    DatabaseManager.salvar_produtos(produtos)
    
    # Restante do código permanece igual...
    
    # Mensagem de confirmação
    mensagem = (
        f"{EMOJIS['sucesso']} *Produto adicionado com sucesso!*\n\n"
        f"{EMOJIS['id']} *ID:* {novo_id}\n"
        f"{EMOJIS['nome']} *Nome:* {context.user_data['nome']}\n"
        f"{EMOJIS['preco']} *Preço:* R$ {context.user_data['preco']:.2f}\n"
    )
    
    if context.user_data.get('previa'):
        mensagem += f"\n{EMOJIS['previa']} *Prévia:* {context.user_data['previa']}"
    
    await update.message.reply_text(
        mensagem,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Limpar os dados temporários
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela a operação atual"""
    await update.message.reply_text(
        "Operação cancelada.",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data.clear()
    return ConversationHandler.END

async def remover_produto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove um produto (admin only)"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text(
            f"{EMOJIS['erro']} Você não tem permissão para usar este comando.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if not context.args:
        await update.message.reply_text(
            f"Uso: /remover <id_do_produto>\n\n"
            f"Use /produtos para ver a lista de produtos e seus IDs.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    produto_id = context.args[0]
    produtos = DatabaseManager.carregar_produtos()
    
    if produto_id in produtos:
        produto_removido = produtos.pop(produto_id)
        DatabaseManager.salvar_produtos(produtos)
        
        await update.message.reply_text(
            f"{EMOJIS['sucesso']} *Produto removido com sucesso!*\n\n"
            f"*Nome:* {produto_removido['nome']}\n"
            f"*ID:* {produto_id}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"{EMOJIS['erro']} Produto com ID {produto_id} não encontrado.",
            parse_mode=ParseMode.MARKDOWN
        )

async def adicionar_previa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona um link de prévia a um produto existente (admin only)"""
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text(
            f"{EMOJIS['erro']} Você não tem permissão para usar este comando.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            f"Uso: /addprevias <id_do_produto> <link_da_previa>\n\n"
            f"Use /produtos para ver a lista de produtos e seus IDs.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    produto_id = context.args[0]
    link_previa = " ".join(context.args[1:])
    
    produtos = DatabaseManager.carregar_produtos()
    
    if produto_id in produtos:
        produtos[produto_id]["previa"] = link_previa
        DatabaseManager.salvar_produtos(produtos)
        
        await update.message.reply_text(
            f"{EMOJIS['sucesso']} *Prévia adicionada com sucesso ao produto!*\n\n"
            f"*ID:* {produto_id}\n"
            f"*Nome:* {produtos[produto_id]['nome']}\n"
            f"*Prévia:* {link_previa}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"{EMOJIS['erro']} Produto com ID {produto_id} não encontrado.",
            parse_mode=ParseMode.MARKDOWN
        )

# ========== HANDLERS DE SEGURANÇA ==========
async def banir_fotos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para banir usuários que enviam fotos não autorizadas"""
    if update.message.from_user.id == ADMIN_ID:
        return
    
    try:
        await update.message.delete()
        await context.bot.ban_chat_member(
            chat_id=update.message.chat_id,
            user_id=update.message.from_user.id
        )
        
        await context.bot.send_message(
            chat_id=update.message.chat_id,
            text=(
                f"{EMOJIS['ban']} Usuário {update.message.from_user.mention_html()} "
                f"foi banido por enviar conteúdo não autorizado!"
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Erro ao banir usuário: {e}")

# ========== CONFIGURAÇÃO DO BOT ==========
def main():
    """Configura e inicia o bot"""
    app = Application.builder().token(TOKEN).build()
    
    # Handlers básicos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("produtos", produtos))
    app.add_handler(CommandHandler("remover", remover_produto))
    app.add_handler(CommandHandler("addprevias", adicionar_previa))
    
    # Handler de conversação para adicionar produtos
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("adicionar", adicionar_produto)],
        states={
            AGUARDANDO_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
            AGUARDANDO_DESCRICAO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_descricao)],
            AGUARDANDO_PRECO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_preco)],
            AGUARDANDO_FOTO: [MessageHandler(filters.PHOTO, receber_foto)],
            AGUARDANDO_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_link)],
            AGUARDANDO_PREVIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_previa)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    app.add_handler(conv_handler)
    
    # Handlers de callback
    app.add_handler(CallbackQueryHandler(comprar_produto, pattern="^comprar_"))
    app.add_handler(CallbackQueryHandler(ver_previa, pattern="^previa_"))
    app.add_handler(CallbackQueryHandler(liberar_acesso, pattern="^liberar_"))
    app.add_handler(CallbackQueryHandler(rejeitar_pagamento, pattern="^rejeitar_"))
    
    # Handlers de mensagens
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.PDF, processar_comprovante))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.User(ADMIN_ID), banir_fotos))
    
    # Iniciar o bot
    logger.info("Bot iniciado e rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()