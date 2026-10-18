from django.contrib import admin
from core.models import *


@admin.register(PlayerWallet)
class PlayerWalletAdmin(admin.ModelAdmin):
    list_display = ('player', 'dracmas', 'total_earned', 'total_spent', 'updated_at')
    search_fields = ('player__username',)
    ordering = ('-dracmas',)
    list_per_page = 50


@admin.register(PlayerCard)
class PlayerCardAdmin(admin.ModelAdmin):
    list_display = ('player', 'card', 'quantity', 'locked_in_market', 'is_foil')
    list_filter = ('is_foil', 'card__rarity')
    search_fields = ('player__username', 'card__name')
    autocomplete_fields = ('player', 'card')
    list_per_page = 100


@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display = (
        'card', 'quantity', 'price_per_unit',
        'seller', 'status', 'created_at'
    )
    list_filter = ('status', 'is_foil', 'card__rarity')
    search_fields = ('card__name', 'seller__username', 'buyer__username')
    autocomplete_fields = ('seller', 'card', 'buyer')
    readonly_fields = ('created_at', 'sold_at')
    date_hierarchy = 'created_at'
    list_per_page = 50

    actions = ['cancelar_anuncios']

    @admin.action(description='Cancelar anúncios selecionados (devolve cartas)')
    def cancelar_anuncios(self, request, queryset):
        count = 0
        for listing in queryset.filter(status='active'):
            if listing.cancel():
                count += 1
        self.message_user(request, f'{count} anúncios cancelados.')


@admin.register(MarketTransaction)
class MarketTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'card', 'quantity', 'total_price',
        'buyer', 'seller', 'created_at'
    )
    list_filter = ('is_foil', 'card__rarity')
    search_fields = ('card__name', 'buyer__username', 'seller__username')
    date_hierarchy = 'created_at'
    list_per_page = 50

    # Desabilita edição (histórico imutável)
    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

@admin.register(God)
class GodAdmin(admin.ModelAdmin):
    list_display = ('name', 'archetype', 'element', 'starting_hp')
    list_filter = ('archetype', 'element')
    search_fields = ('name', 'play_style', 'divine_power_name')
    fieldsets = (
        ('Identidade', {
            'fields': ('name', 'description', 'element', 'archetype', 'play_style')
        }),
        ('Poder Divino', {
            'fields': ('divine_power_name', 'divine_power_description', 'divine_power_cost', 'divine_power_effect')
        }),
        ('Mecânica Exclusiva', {
            'fields': ('exclusive_mechanic_name', 'exclusive_mechanic_description')
        }),
        ('Configuração', {
            'fields': ('starting_hp',)
        }),
    )


@admin.register(CardClass)
class CardClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_neural')
    list_filter = ('is_neural',)
    search_fields = ('name',)
    filter_horizontal = ('associated_gods',)


@admin.register(CardType)
class CardTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Rarity)
class RarityAdmin(admin.ModelAdmin):
    list_display = ('name', 'color_code')
    search_fields = ('name',)


@admin.register(Ability)
class AbilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code_identifier')
    search_fields = ('name', 'description')


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('name', 'card_type', 'rarity', 'cost', 'attack', 'health', 'is_legendary')
    list_filter = ('card_type', 'rarity', 'is_legendary', 'card_class')
    search_fields = ('name', 'description')
    filter_horizontal = ('abilities',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('name', 'card_type', 'rarity', 'card_class')
        }),
        ('Atributos', {
            'fields': ('cost', 'attack', 'health')
        }),
        ('Efeito', {
            'fields': ('description', 'abilities', 'image_url')
        }),
        ('Configuração', {
            'fields': ('is_legendary',)
        }),
    )


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'god', 'card_count')
    list_filter = ('god',)
    search_fields = ('name', 'owner__username')
    
    def card_count(self, obj):
        return obj.card_count()
    card_count.short_description = 'Total Cartas'


@admin.register(DeckCard)
class DeckCardAdmin(admin.ModelAdmin):
    list_display = ('deck', 'card', 'quantity')
    list_filter = ('deck',)
    search_fields = ('card__name',)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at', 'started_at', 'finished_at', 'winner')
    list_filter = ('status',)
    search_fields = ('players__username',)


@admin.register(PlayerGame)
class PlayerGameAdmin(admin.ModelAdmin):
    list_display = ('player', 'game', 'deck', 'is_first_player', 'patron_god_hp', 'current_faith', 'turn_number')
    list_filter = ('is_first_player', 'game')
    search_fields = ('player__username',)


@admin.register(PlayerHandCard)
class PlayerHandCardAdmin(admin.ModelAdmin):
    list_display = ('player_game', 'card', 'is_temporary')
    search_fields = ('player_game__player__username', 'card__name')


@admin.register(PlayerBoardCard)
class PlayerBoardCardAdmin(admin.ModelAdmin):
    list_display = ('player_game', 'card', 'current_health', 'current_attack', 'has_attacked', 'can_attack', 'position')
    search_fields = ('player_game__player__username', 'card__name')


@admin.register(GameTurn)
class GameTurnAdmin(admin.ModelAdmin):
    list_display = ('game', 'player_game', 'turn_number', 'started_at', 'faith_generated')
    list_filter = ('turn_number',)
    search_fields = ('player_game__player__username',)