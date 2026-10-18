from django.db import models
from django.contrib.auth.models import User
import random


class God(models.Model):
    """Deus Patrono - the player's patron god"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    starting_hp = models.IntegerField(default=30)
    # Class/element type for deck restrictions
    element = models.CharField(max_length=50, default="Neutral")

    # Divine Power details
    divine_power_name = models.CharField(max_length=100, default="Poder Divino")
    divine_power_description = models.TextField(blank=True)
    divine_power_cost = models.IntegerField(default=2)  # Custo em Fé
    divine_power_effect = models.CharField(max_length=200, blank=True, default="Causa 1 de dano")

    # Game identity/archetype
    archetype = models.CharField(max_length=50, default="Controle")  # Controle, Aggro, Midrange, Combo
    play_style = models.TextField(blank=True)  # Estilo de jogo (ex: "Parecido com Mago")

    # Exclusive mechanic
    exclusive_mechanic_name = models.CharField(max_length=100, blank=True)
    exclusive_mechanic_description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.archetype})"


class CardClass(models.Model):
    """Classe da carta (Neutra ou atrelada a um Deus)"""
    name = models.CharField(max_length=50, unique=True)
    associated_gods = models.ManyToManyField(God, blank=True)
    is_neural = models.BooleanField(default=True)  # True = Neutral, False = Specific God

    def __str__(self):
        return self.name


class CardType(models.Model):
    """Type of card (Monster, Spell, Relic, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Rarity(models.Model):
    """Card rarity"""
    name = models.CharField(max_length=50, unique=True)
    color_code = models.CharField(max_length=7, default="#808080")  # hex color

    def __str__(self):
        return self.name


class Card(models.Model):
    """A card in the game"""
    name = models.CharField(max_length=100)
    card_type = models.ForeignKey(CardType, on_delete=models.CASCADE)
    rarity = models.ForeignKey(Rarity, on_delete=models.CASCADE)
    cost = models.IntegerField(default=0)  # Faith cost to play (0 a 10)
    attack = models.IntegerField(default=0)  # Damage dealt (Monstros/Heróis e Relíquias)
    health = models.IntegerField(default=0)  # Durabilidade - dano que pode receber
    card_class = models.ForeignKey(CardClass, on_delete=models.CASCADE, null=True, blank=True)
    description = models.TextField(blank=True)  # Texto/Efeito especial (ex: "Grito de Guerra: Compre uma carta")
    abilities = models.ManyToManyField('Ability', blank=True)
    image_url = models.URLField(blank=True)
    is_legendary = models.BooleanField(default=False)

    class Meta:
        unique_together = ('name', 'card_type')

    def __str__(self):
        return self.name


class Ability(models.Model):
    """Special abilities that cards can have"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    code_identifier = models.CharField(max_length=100, blank=True)  # for logic mapping

    def __str__(self):
        return self.name


class Deck(models.Model):
    """Um baralho de 20 a 30 cartas"""
    MIN_CARDS = 20
    MAX_CARDS = 30

    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100, default="Meu Baralho")
    god = models.ForeignKey(God, on_delete=models.CASCADE, null=True, blank=True)
    cards = models.ManyToManyField(Card, through='DeckCard')

    def __str__(self):
        return f"{self.name} - {self.god.name if self.god else 'Neutral'}"

    def can_add_card(self, card):
        """Check if a card can be added to the deck (max 2 copies, 1 for legendaries)"""
        existing = DeckCard.objects.filter(deck=self, card=card).count()
        max_copies = 1 if card.is_legendary else 2
        return existing < max_copies

    def add_card(self, card):
        """Add a card to the deck if allowed"""
        if self.can_add_card(card):
            DeckCard.objects.create(deck=self, card=card)
            return True
        return False

    def card_count(self):
        """Total de cartas no deck (soma das quantidades, não só as linhas)"""
        total = DeckCard.objects.filter(deck=self).aggregate(total=models.Sum('quantity'))['total']
        return total or 0

    def is_valid(self):
        """Deck must have at least 20 cards (and at most 30) to battle"""
        count = self.card_count()
        return self.MIN_CARDS <= count <= self.MAX_CARDS


class DeckCard(models.Model):
    """Intermediate model for deck-card relationship"""
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)


class Game(models.Model):
    """Uma instância de jogo"""
    STATUS_CHOICES = [
        ('waiting', 'Waiting for Players'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]
    players = models.ManyToManyField(User, through='PlayerGame', related_name='games')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')

    def __str__(self):
        return f"Game {self.id}"


class PlayerGame(models.Model):
    """Participação de um jogador no jogo"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey(User, on_delete=models.CASCADE)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE)
    is_first_player = models.BooleanField(default=False)  # True = joga primeiro (turno 1)
    patron_god_hp = models.IntegerField(default=30)
    current_faith = models.IntegerField(default=1)  # Começa com 1 no turno 1
    max_faith = models.IntegerField(default=10)
    turn_number = models.IntegerField(default=1)
    actions_remaining = models.IntegerField(default=3)  # Ações por turno
    hand_limit = models.IntegerField(default=10)
    board_limit = models.IntegerField(default=7)  # Máximo de criaturas no campo

    class Meta:
        unique_together = ('game', 'player')

    def __str__(self):
        return f"{self.player.username} in Game {self.game.id} (HP: {self.patron_god_hp}, Turn: {self.turn_number})"


class PlayerHandCard(models.Model):
    """Cartas na mão do jogador"""
    player_game = models.ForeignKey(PlayerGame, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    is_temporary = models.BooleanField(default=False)  # For the extra Faith/Mana card

    def __str__(self):
        return f"{self.player_game.player.username}'s {self.card.name}"


class PlayerBoardCard(models.Model):
    """Criaturas no tabuleiro"""
    player_game = models.ForeignKey(PlayerGame, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE)
    current_health = models.IntegerField(default=0)
    current_attack = models.IntegerField(default=0)
    has_attacked = models.BooleanField(default=False)
    can_attack = models.BooleanField(default=True)
    position = models.IntegerField(default=0)  # Ordem no tabuleiro

    def __str__(self):
        return f"{self.player_game.player.username}'s {self.card.name} (HP: {self.current_health})"


class GameTurn(models.Model):
    """Controla as turnos do jogo"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player_game = models.ForeignKey(PlayerGame, on_delete=models.CASCADE)
    turn_number = models.IntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    faith_generated = models.IntegerField(default=0)  # Quantidade de fé gerada este turno

    def __str__(self):
        return f"Turn {self.turn_number} - {self.player_game.player.username}"


# ============================================================
# MERCADO DE CARTAS
# ============================================================

class PlayerWallet(models.Model):
    """
    Carteira de Dracmas (moeda do jogo) de cada jogador.
    Relação 1-para-1 com User — criada automaticamente via signal
    ou no primeiro acesso.
    """
    player = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='wallet',
        verbose_name='Jogador'
    )
    dracmas = models.IntegerField(
        default=500,
        verbose_name='Dracmas',
        help_text='Moeda do jogo usada para comprar cartas no mercado'
    )

    # Auditoria — útil pra debugar economia
    total_earned = models.IntegerField(
        default=0,
        verbose_name='Total ganho',
        help_text='Soma de todas as dracmas ganhas (histórico)'
    )
    total_spent = models.IntegerField(
        default=0,
        verbose_name='Total gasto',
        help_text='Soma de todas as dracmas gastas (histórico)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Carteira'
        verbose_name_plural = 'Carteiras'
        indexes = [
            models.Index(fields=['-dracmas']),  # ranking de riqueza
        ]

    def __str__(self):
        return f"{self.player.username}: {self.dracmas}💠"

    # ---------- Métodos de negócio ----------
    def can_afford(self, amount: int) -> bool:
        """Verifica se o jogador tem saldo suficiente"""
        return self.dracmas >= amount

    def add(self, amount: int) -> None:
        """Adiciona dracmas e registra no histórico"""
        if amount < 0:
            raise ValueError("Use .spend() para débitos")
        self.dracmas += amount
        self.total_earned += amount
        self.save(update_fields=['dracmas', 'total_earned', 'updated_at'])

    def spend(self, amount: int) -> bool:
        """
        Tenta gastar dracmas. Retorna True se conseguiu, False se saldo insuficiente.
        """
        if amount < 0:
            raise ValueError("Valor deve ser positivo")
        if not self.can_afford(amount):
            return False
        self.dracmas -= amount
        self.total_spent += amount
        self.save(update_fields=['dracmas', 'total_spent', 'updated_at'])
        return True


class PlayerCard(models.Model):
    """
    Inventário do jogador — quantas cópias ele possui de cada carta.
    Suporta versão foil (brilhante) como item separado.
    """
    player = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='collection',
        verbose_name='Jogador'
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='owners',
        verbose_name='Carta'
    )
    quantity = models.IntegerField(
        default=0,
        verbose_name='Quantidade',
        help_text='Número de cópias que o jogador possui'
    )
    is_foil = models.BooleanField(
        default=False,
        verbose_name='Foil',
        help_text='Versão brilhante/especial da carta'
    )

    # Controle de "cartas travadas em anúncios"
    locked_in_market = models.IntegerField(
        default=0,
        verbose_name='Travadas no mercado',
        help_text='Cópias atualmente anunciadas (não disponíveis para uso)'
    )

    first_obtained_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Carta do jogador'
        verbose_name_plural = 'Cartas dos jogadores'
        unique_together = ('player', 'card', 'is_foil')
        indexes = [
            models.Index(fields=['player', 'card']),
            models.Index(fields=['player', '-quantity']),
        ]

    def __str__(self):
        foil = ' ✨' if self.is_foil else ''
        return f"{self.player.username} — {self.card.name}{foil} x{self.quantity}"

    # ---------- Propriedades ----------
    @property
    def available(self) -> int:
        """Cópias disponíveis (descontando as travadas em anúncios)"""
        return max(0, self.quantity - self.locked_in_market)

    @property
    def max_deckable(self) -> int:
        """Quantas cópias podem ir pro deck (respeitando lendárias)"""
        return 1 if self.card.is_legendary else 2

    # ---------- Métodos ----------
    def add(self, amount: int = 1) -> None:
        self.quantity += amount
        self.save(update_fields=['quantity', 'updated_at'])

    def remove(self, amount: int = 1) -> bool:
        """Remove cópias disponíveis. Retorna False se não tiver o suficiente."""
        if self.available < amount:
            return False
        self.quantity -= amount
        if self.quantity <= 0:
            self.delete()
        else:
            self.save(update_fields=['quantity', 'updated_at'])
        return True

    def lock_for_market(self, amount: int) -> bool:
        """Trava cópias para um anúncio"""
        if self.available < amount:
            return False
        self.locked_in_market += amount
        self.save(update_fields=['locked_in_market', 'updated_at'])
        return True

    def unlock_from_market(self, amount: int) -> None:
        """Destrava cópias (anúncio cancelado/expirado)"""
        self.locked_in_market = max(0, self.locked_in_market - amount)
        self.save(update_fields=['locked_in_market', 'updated_at'])


class MarketListing(models.Model):
    """
    Anúncio de venda de uma carta no mercado.
    As cartas ficam 'travadas' no inventário do vendedor enquanto o anúncio
    estiver ativo (PlayerCard.locked_in_market).
    """
    STATUS_CHOICES = [
        ('active',    'Ativo'),
        ('sold',      'Vendido'),
        ('cancelled', 'Cancelado'),
        ('expired',   'Expirado'),
    ]

    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='listings',
        verbose_name='Vendedor'
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='listings',
        verbose_name='Carta'
    )
    quantity = models.IntegerField(
        default=1,
        verbose_name='Quantidade',
        help_text='Quantas cópias estão à venda'
    )
    price_per_unit = models.IntegerField(
        default=100,
        verbose_name='Preço unitário (💠)',
        help_text='Preço em dracmas por cópia'
    )

    # Carta foil?
    is_foil = models.BooleanField(
        default=False,
        verbose_name='Foil'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name='Status'
    )

    # Comprador (preenchido quando vendido)
    buyer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases',
        verbose_name='Comprador'
    )
    sold_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Vendido em'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Expira em',
        help_text='Se vazio, o anúncio não expira'
    )

    class Meta:
        verbose_name = 'Anúncio'
        verbose_name_plural = 'Anúncios'
        ordering = ['price_per_unit', '-created_at']  # mais baratos primeiro
        indexes = [
            models.Index(fields=['status', 'price_per_unit']),   # busca do mercado
            models.Index(fields=['seller', 'status']),           # meus anúncios
            models.Index(fields=['card', 'status']),             # cartas disponíveis
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        foil = ' ✨' if self.is_foil else ''
        return (
            f"{self.card.name}{foil} x{self.quantity} — "
            f"{self.price_per_unit}💠 ({self.seller.username}) [{self.status}]"
        )

    # ---------- Propriedades ----------
    @property
    def total_price(self) -> int:
        """Preço total do anúncio (todas as cópias)"""
        return self.price_per_unit * self.quantity

    @property
    def is_active(self) -> bool:
        return self.status == 'active'

    @property
    def is_expired(self) -> bool:
        """Verifica se passou da data de expiração"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

    # ---------- Métodos ----------
    def cancel(self) -> bool:
        """Cancela o anúncio e devolve as cartas travadas ao vendedor"""
        if self.status != 'active':
            return False

        # Destrava no inventário do vendedor
        pc = PlayerCard.objects.filter(
            player=self.seller,
            card=self.card,
            is_foil=self.is_foil
        ).first()
        if pc:
            pc.unlock_from_market(self.quantity)

        self.status = 'cancelled'
        self.save(update_fields=['status'])
        return True

    def expire(self) -> bool:
        """Marca como expirado e devolve cartas"""
        if self.status != 'active':
            return False

        pc = PlayerCard.objects.filter(
            player=self.seller,
            card=self.card,
            is_foil=self.is_foil
        ).first()
        if pc:
            pc.unlock_from_market(self.quantity)

        self.status = 'expired'
        self.save(update_fields=['status'])
        return True


class MarketTransaction(models.Model):
    """
    Histórico imutável de cada transação concluída.
    Nunca é editado — apenas criado (auditoria).
    """
    listing = models.ForeignKey(
        MarketListing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Anúncio'
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions_bought',
        verbose_name='Comprador'
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions_sold',
        verbose_name='Vendedor'
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Carta'
    )
    quantity = models.IntegerField(
        default=1,
        verbose_name='Quantidade'
    )
    price_per_unit = models.IntegerField(
        default=0,
        verbose_name='Preço unitário'
    )
    total_price = models.IntegerField(
        default=0,
        verbose_name='Preço total'
    )
    is_foil = models.BooleanField(default=False, verbose_name='Foil')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Transação'
        verbose_name_plural = 'Transações'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['buyer', '-created_at']),
            models.Index(fields=['seller', '-created_at']),
            models.Index(fields=['card', '-created_at']),
        ]

    def __str__(self):
        return (
            f"{self.card.name} x{self.quantity} — "
            f"{self.total_price}💠 ({self.buyer.username} ← {self.seller.username})"
        )

    # ---------- Propriedades ----------
    @property
    def tax_amount(self) -> int:
        """Taxa de 5% que o jogo poderia cobrar (opcional)"""
        return int(self.total_price * 0.05)

    @property
    def seller_received(self) -> int:
        """Quanto o vendedor recebeu líquido (após tax)"""
        return self.total_price - self.tax_amount

    def save(self, *args, **kwargs):
        """Impede edição depois de criado — histórico é imutável"""
        if self.pk:
            raise ValueError("MarketTransaction é imutável e não pode ser editada.")
        super().save(*args, **kwargs)


# ============================================================
# SIGNALS — cria carteira automaticamente
# ============================================================

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_player_wallet(sender, instance, created, **kwargs):
    """Cria carteira automaticamente quando um User é criado"""
    if created:
        PlayerWallet.objects.get_or_create(player=instance)