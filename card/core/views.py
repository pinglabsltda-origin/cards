from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from core.models import Deck, Card, God, DeckCard, PlayerWallet, MarketListing, PlayerCard, MarketTransaction, Rarity, CardType, CardClass
from core.game_engine import GameEngine
import json
from django.db import transaction
from django.utils import timezone


def home_view(request):
    """Home page view"""
    return render(request, 'home.html')


@login_required
def board_view(request):
    """View for the game board that passes initial card data to template"""
    # Get the player's deck (assuming they have one)
    player_deck = None
    user_decks = list(Deck.objects.filter(owner=request.user))
    # Usa o deck com mais cartas (o deck que o jogador montou para batalhar)
    player_deck = max(user_decks, key=lambda d: d.card_count(), default=None)
    if player_deck is None:
        # Cria um deck padrão para testes
        god = God.objects.first()  # Zeus
        player_deck = Deck.objects.create(
            owner=request.user,
            name="Deck Inicial",
            god=god
        )
    
    # Get cards from deck (simulate initial hand)
    card_data = []
    deck_cards = player_deck.cards.all()[:10]
    
    for card in deck_cards:
        card_info = {
            'id': card.id,
            'name': card.name,
            'cost': card.cost,
            'attack': card.attack,
            'health': card.health,
            'type': card.card_type.name,
            'rarity': card.rarity.name,
            'image_url': card.image_url or '/static/cards/placeholder.png',
            'is_temporary': False
        }
        card_data.append(card_info)
    
    # Formats cards for frontend (maps DB fields to JS fields)
    card_data_for_js = []
    # Use first 4 cards for initial hand
    initial_cards = player_deck.cards.all()[:4]
    
    for card in initial_cards:
        card_data_for_js.append({
            'id': str(card.id),
            'nome': card.name,
            'tipo': card.card_type.name,
            'custo': card.cost,
            'atk': card.attack,
            'hp': card.health,
            'uid': 'c-' + str(card.id),
            'icone': '🛡️',  # default icon
            'hpAtual': card.health,
            'podeAtacar': False
        })
    
    # All deck cards for CARDS_DB fallback
    all_cards = []
    for card in player_deck.cards.all()[:30]:  # up to 30 cards from deck
        all_cards.append({
            'id': str(card.id),
            'nome': card.name,
            'tipo': card.card_type.name,
            'custo': card.cost,
            'atk': card.attack,
            'hp': card.health,
            'icone': '🛡️',
            'uid': 'c-' + str(card.id),
            'hpAtual': card.health,
            'podeAtacar': False
        })
    
    context = {
        'cards': card_data_for_js,
        'player': request.user,
        'game_active': True,
        'cards_db_json': json.dumps(all_cards) if all_cards else '[]'
    }
    
    return render(request, 'game/board.html', context)

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import PlayerGame, PlayerHandCard, PlayerBoardCard

@login_required
@require_POST
def play_card_api(request):
    try:
        # Pega os dados enviados pelo Javascript
        data = json.loads(request.body)
        card_id = data.get('card_id')

        # No futuro, passaremos o game_id real. Por enquanto, pegamos o jogo ativo do player.
        player_game = PlayerGame.objects.filter(player=request.user).first()
        
        if not player_game:
            return JsonResponse({'status': 'error', 'message': 'Jogo não encontrado.'}, status=400)

        # 1. Valida se a carta está realmente na MÃO do jogador
        hand_card = PlayerHandCard.objects.filter(player_game=player_game, card_id=card_id).first()
        if not hand_card:
            return JsonResponse({'status': 'error', 'message': 'Você não tem essa carta na mão.'}, status=400)

        # 2. Valida se tem FÉ (Mana) suficiente
        card = hand_card.card
        if player_game.current_faith < card.cost:
            return JsonResponse({'status': 'error', 'message': 'Fé insuficiente!'}, status=400)

        # 3. Valida limite de criaturas na mesa (Regra: máximo 7)
        board_count = PlayerBoardCard.objects.filter(player_game=player_game).count()
        if board_count >= player_game.board_limit and card.card_type.name in ['Herói', 'Monstro']:
            return JsonResponse({'status': 'error', 'message': 'Sua mesa está cheia!'}, status=400)

        # SE PASSOU EM TODAS AS VALIDAÇÕES, EXECUTA A JOGADA:
        
        # A) Deduz a Fé do jogador
        player_game.current_faith -= card.cost
        player_game.save()

        # B) Se for monstro/herói, coloca na mesa
        if card.card_type.name in ['Herói', 'Monstro']:
            PlayerBoardCard.objects.create(
                player_game=player_game,
                card=card,
                current_health=card.health,
                current_attack=card.attack
                # Aqui no futuro definiremos a 'position' (slot 1 a 7)
            )
        
        # C) Se for feitiço/relíquia, o tratamento será diferente (vamos focar nos monstros primeiro)

        # D) Remove a carta da mão do jogador
        hand_card.delete()

        # Retorna sucesso para o Frontend atualizar a tela
        return JsonResponse({
            'status': 'success',
            'new_faith': player_game.current_faith,
            'message': f'{card.name} invocado com sucesso!'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def login_view(request):
    """Custom login view that renders our login template"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'⚡ Bem-vindo de volta, {user.username}!')
            
            # Redirect to next page if specified, otherwise home
            next_page = request.GET.get('next', 'home')
            return redirect(next_page)
        else:
            error = 'Nome de usuário ou senha inválidos.'
            return render(request, 'login.html', {'error': error})
    
    # GET request - show login form
    error = request.GET.get('error', '')
    context = {
        'error': error if error else None
    }
    return render(request, 'login.html', context)


@login_required
def my_cards_view(request):
    """View para o usuário gerenciar sua coleção e deck."""
    # Todas as cartas do jogo (para o catálogo)
    all_cards = Card.objects.all()

    # Simula coleção: No momento, assumimos que o jogador tem acesso a todas (ou implemente PlayerCollection)
    # Aqui vou buscar do DeckCard se o usuário já tem um deck
    player_deck = Deck.objects.filter(owner=request.user).first()
    
    current_deck = {}
    if player_deck:
        deck_cards = DeckCard.objects.filter(deck=player_deck)
        for dc in deck_cards:
            current_deck[dc.card.id] = dc.quantity

    # Serializa cartas para o JS
    cards_json = []
    for c in all_cards:
        cards_json.append({
            'id': str(c.id),
            'nome': c.name,
            'tipo': c.card_type.name,
            'custo': c.cost,
            'atk': c.attack,
            'hp': c.health,
            'icone': '🛡️', # Default ou mapear via c.image_url se for emoji
            'raridade': c.rarity.name,
            'coletadas': 3, # O jogador possui até 3 cópias de cada carta
        })

    context = {
        'all_cards_json': json.dumps(cards_json),
        'current_deck_json': json.dumps(current_deck),
    }
    
    return render(request, 'user/mycards.html', context)


@login_required
@require_POST
def save_deck_api(request):
    """Salva a composição do deck do jogador."""
    try:
        data = json.loads(request.body)
        new_deck_data = data.get('deck', {}) # { card_id: quantity }
        
        # Validação de tamanho
        total_cards = sum(new_deck_data.values())
        if total_cards < Deck.MIN_CARDS or total_cards > Deck.MAX_CARDS:
            return JsonResponse({
                'status': 'error',
                'message': f'O deck deve ter entre {Deck.MIN_CARDS} e {Deck.MAX_CARDS} cartas.'
            }, status=400)
            
        # Busca ou cria o deck do usuário
        deck, created = Deck.objects.get_or_create(
            owner=request.user, 
            defaults={'name': "Meu Baralho Principal"}
        )
        
        # Limpa o deck atual e reconstrói
        DeckCard.objects.filter(deck=deck).delete()
        
        for card_id, qty in new_deck_data.items():
            card = Card.objects.get(id=card_id)
            DeckCard.objects.create(deck=deck, card=card, quantity=qty)
            
        return JsonResponse({'status': 'success', 'message': 'Deck salvo com sucesso!'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('home')


@login_required
def market_view(request):
    """Renderiza a página do mercado"""

    # Carteira do jogador
    wallet, _ = PlayerWallet.objects.get_or_create(player=request.user)

    # Anúncios ativos
    listings = MarketListing.objects.filter(
        status='active'
    ).select_related('card', 'card__rarity', 'card__card_type', 'card__card_class', 'seller')

    listings_json = [
        {
            'id': l.id,
            'card': {
                'id': l.card.id,
                'name': l.card.name,
                'type': l.card.card_type.name,
                'rarity': l.card.rarity.name,
                'rarity_color': l.card.rarity.color_code,
                'cost': l.card.cost,
                'attack': l.card.attack,
                'health': l.card.health,
                'emoji': l.card.image_url or '🃏',  # ou um mapping
                'class': l.card.card_class.name if l.card.card_class else 'Neutral',
            },
            'quantity': l.quantity,
            'price_per_unit': l.price_per_unit,
            'seller': l.seller.username,
            'seller_id': l.seller.id,
            'created_at': l.created_at.isoformat(),
        }
        for l in listings
    ]

    # Coleção do jogador
    collection = PlayerCard.objects.filter(
        player=request.user, quantity__gt=0
    ).select_related('card')

    collection_json = [
        {
            'card': {
                'id': pc.card.id,
                'name': pc.card.name,
                'emoji': pc.card.image_url or '🃏',
            },
            'quantity': pc.quantity,
        }
        for pc in collection
    ]

    # Filtros
    rarities_json = [
        {'name': r.name, 'color': r.color_code}
        for r in Rarity.objects.all()
    ]
    types_json = [{'name': t.name} for t in CardType.objects.all()]
    classes_json = [{'name': c.name} for c in CardClass.objects.all()]

    return render(request, 'game/market.html', {
        'wallet': wallet,
        'listings_json': json.dumps(listings_json),
        'collection_json': json.dumps(collection_json),
        'rarities_json': json.dumps(rarities_json),
        'card_types_json': json.dumps(types_json),
        'card_classes_json': json.dumps(classes_json),
    })


@login_required
@require_POST
@transaction.atomic
def market_buy(request):
    """Compra uma carta do mercado"""
    try:
        payload = json.loads(request.body)
        listing_id = payload.get('listing_id')
        quantity = int(payload.get('quantity', 1))

        listing = get_object_or_404(MarketListing, id=listing_id, status='active')

        if listing.seller == request.user:
            return JsonResponse({'status': 'error', 'message': 'Você não pode comprar seu próprio anúncio.'}, status=400)

        if quantity > listing.quantity:
            return JsonResponse({'status': 'error', 'message': 'Quantidade indisponível.'}, status=400)

        # Verifica saldo
        wallet, _ = PlayerWallet.objects.get_or_create(player=request.user)
        total_price = listing.price_per_unit * quantity

        if wallet.dracmas < total_price:
            return JsonResponse({
                'status': 'error',
                'message': f'Dracmas insuficientes. Você tem {wallet.dracmas}💠.'
            }, status=400)

        # Debita do comprador (usando método do modelo)
        wallet.spend(total_price)

        # Credita o vendedor (usando método do modelo)
        seller_wallet.add(total_price)

        # Adiciona carta ao inventário do comprador
        pc, _ = PlayerCard.objects.get_or_create(
            player=request.user, card=listing.card, is_foil=False
        )
        pc.add(quantity)

        # Remove do inventário do vendedor (usando método do modelo)
        seller_pc = PlayerCard.objects.filter(
            player=listing.seller, card=listing.card, is_foil=False
        ).first()
        if seller_pc:
            seller_pc.remove(quantity)

        # Atualiza listing
        listing.quantity -= quantity
        if listing.quantity <= 0:
            listing.status = 'sold'
            listing.buyer = request.user
            listing.sold_at = timezone.now()
        listing.save()

        # Histórico
        MarketTransaction.objects.create(
            listing=listing,
            buyer=request.user,
            seller=listing.seller,
            card=listing.card,
            quantity=quantity,
            total_price=total_price,
        )

        return JsonResponse({
            'status': 'success',
            'new_balance': wallet.dracmas,
            'message': f'Comprou {listing.card.name} x{quantity}!'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
@require_POST
@transaction.atomic
def market_sell(request):
    """Cria um anúncio de venda"""
    try:
        payload = json.loads(request.body)
        card_id = payload.get('card_id')
        quantity = int(payload.get('quantity', 1))
        price = int(payload.get('price_per_unit', 0))

        if quantity < 1 or price < 1:
            return JsonResponse({'status': 'error', 'message': 'Valores inválidos.'}, status=400)

        card = get_object_or_404(Card, id=card_id)

        # Verifica se o jogador tem as cartas suficientes (descontando as travadas)
        pc = PlayerCard.objects.filter(
            player=request.user, card=card, is_foil=False
        ).first()

        if not pc or pc.available < quantity:
            return JsonResponse({
                'status': 'error',
                'message': f'Você não tem {quantity} cópias disponíveis de {card.name}.'
            }, status=400)

        # Trava as cartas para o anúncio (não remove do inventário)
        pc.lock_for_market(quantity)

        # Cria anúncio
        listing = MarketListing.objects.create(
            seller=request.user,
            card=card,
            quantity=quantity,
            price_per_unit=price,
            status='active',
        )

        return JsonResponse({
            'status': 'success',
            'message': f'{card.name} x{quantity} anunciado por {price}💠!',
            'listing': {
                'id': listing.id,
                'card': {
                    'id': card.id,
                    'name': card.name,
                    'type': card.card_type.name,
                    'rarity': card.rarity.name,
                    'rarity_color': card.rarity.color_code,
                    'cost': card.cost,
                    'attack': card.attack,
                    'health': card.health,
                    'emoji': card.image_url or '🃏',
                    'class': card.card_class.name if card.card_class else 'Neutral',
                },
                'quantity': listing.quantity,
                'price_per_unit': listing.price_per_unit,
                'seller': request.user.username,
                'seller_id': request.user.id,
                'created_at': listing.created_at.isoformat(),
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
