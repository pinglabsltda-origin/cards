import random
from django.utils import timezone
from datetime import timedelta


class GameEngine:
    """Engine for managing game mechanics"""
    
    def __init__(self, player_game):
        self.player_game = player_game
        self.game = player_game.game
        self.deck = player_game.deck
        self.players = self.game.players.all()
        
    def start_game(self):
        """Inicializa o jogo"""
        # Verifica se o jogo está válido
        if self.game.status != 'waiting':
            raise ValueError("Game is not in waiting state")
            
        # Configura o primeiro jogador
        if not self.player_game.is_first_player:
            # O primeiro jogador é aquele que começa o jogo
            self.player_game.is_first_player = True
            self.player_game.save()
            
        # Inicializa o estado do jogo
        self.game.status = 'in_progress'
        self.game.started_at = timezone.now()
        self.game.save()
        
        # Distribui cartas iniciais
        self._deal_starting_cards()
        
        # Configura o primeiro turno
        self._reset_turn_state()
        
        return True
        
    def _deal_starting_cards(self):
        """Distribui cartas iniciais para os jogadores"""
        # Primeiro jogador recebe 3 cartas
        player_cards = self.deck.cards.all()[:3]
        for card in player_cards:
            PlayerHandCard.objects.create(
                player_game=self.player_game, 
                card=card,
                is_temporary=False
            )
            
        # Segundo jogador recebe 4 cartas + carta temporária
        second_player = self._get_second_player()
        second_player_cards = self.deck.cards.all()[3:7]  # 4 cartas
        for card in second_player_cards:
            PlayerHandCard.objects.create(
                player_game=second_player,
                card=card,
                is_temporary=False
            )
            
        # Carta temporária de Fé/Mana para o segundo jogador
        faith_card = Card.objects.get(name="Fé/Mana Temporária")
        PlayerHandCard.objects.create(
            player_game=second_player,
            card=faith_card,
            is_temporary=True
        )
        
    def _get_second_player(self):
        """Obtém o segundo jogador (não é o primeiro)"""
        for player in self.players:
            if player != self.player_game and player.is_first_player == False:
                return player
        return None
        
    def _reset_turn_state(self):
        """Reseta o estado do turno"""
        self.player_game.turn_number = 1
        self.player_game.current_faith = 1  # Começa com 1 fé no turno 1
        self.player_game.actions_remaining = 3  # 3 ações por turno
        self.player_game.has_attacked = False
        self.player_game.save()
        
        # Gera fé para o próximo turno
        self._generate_faith_for_next_turn()
        
    def _generate_faith_for_next_turn(self):
        """Gera fé para o próximo turno"""
        # Fé aumenta +1 a cada turno até o limite de 10
        new_faith = min(self.player_game.max_faith, self.player_game.current_faith + 1)
        self.player_game.current_faith = new_faith
        self.player_game.save()
        
    def generate_faith_for_turn(self):
        """Gera fé no início do turno"""
        if self.player_game.turn_number > 1:
            # Gera fé no início de cada turno após o primeiro
            self._generate_faith_for_next_turn()
            
    def reset_actions(self):
        """Reseta as ações restantes para o novo turno"""
        self.player_game.actions_remaining = 3
        self.player_game.has_attacked = False
        self.player_game.save()
        
    def increase_actions(self, amount=1):
        """Aumenta as ações restantes"""
        self.player_game.actions_remaining += amount
        if self.player_game.actions_remaining > 3:
            self.player_game.actions_remaining = 3
        self.player_game.save()
        
    def decrease_actions(self, amount=1):
        """Diminui as ações restantes"""
        self.player_game.actions_remaining = max(0, self.player_game.actions_remaining - amount)
        self.player_game.save()
        
    def can_play_card(self, card):
        """Verifica se o jogador pode jogar a carta"""
        if card.cost > self.player_game.current_faith:
            return False
            
        if card.cost > self.player_game.max_faith:
            return False
            
        # Verifica limite de cartas na mão
        hand_size = PlayerHandCard.objects.filter(
            player_game=self.player_game,
            is_temporary=False
        ).count()
        
        if hand_size >= self.player_game.hand_limit:
            return False
            
        return True
        
    def play_card(self, card, target_card=None):
        """Joga uma carta"""
        if not self.can_play_card(card):
            return False
            
        # Consome fé
        self.player_game.current_faith -= card.cost
        self.player_game.save()
        
        # Cria a carta no tabuleiro (se for criatura)
        if card.attack > 0 or card.health > 0:
            PlayerBoardCard.objects.create(
                player_game=self.player_game,
                card=card,
                current_health=card.health,
                current_attack=card.attack,
                position=self._get_next_board_position()
            )
            
        # Remove da mão
        PlayerHandCard.objects.filter(
            player_game=self.player_game,
            card=card,
            is_temporary=False
        ).delete()
        
        return True
        
    def _get_next_board_position(self):
        """Obtém a próxima posição livre no tabuleiro"""
        occupied_positions = PlayerBoardCard.objects.filter(
            player_game=self.player_game
        ).values_list('position', flat=True)
        
        for pos in range(self.player_game.board_limit):
            if pos not in occupied_positions:
                return pos
                
        return 0  # Fallback
        
    def end_turn(self):
        """Finaliza o turno"""
        # Reseta ações
        self.decrease_actions(1)  # Consome uma ação ao finalizar
        
        # Próximo jogador
        current_player = self.player_game
        second_player = self._get_second_player()
        
        if current_player.is_first_player:
            # Troca para o segundo jogador
            self.player_game = second_player
        else:
            # Volta para o primeiro jogador
            self.player_game = self._get_first_player()
            
        # Atualiza turno
        self.player_game.turn_number += 1
        self.player_game.has_attacked = False
        self.player_game.save()
        
        # Gera fé para o novo turno
        self._generate_faith_for_next_turn()
        
        # Verifica vitória
        if self.check_victory():
            return True
            
        return False
        
    def _get_first_player(self):
        """Obtém o primeiro jogador do jogo"""
        for player in self.players:
            if player.deck == self.deck:
                return player
        return None
        
    def check_victory(self):
        """Verifica se alguém venceu"""
        # Verifica se o Deus Patrono inimigo está com 0 HP
        for player in self.players:
            if player.patron_god_hp <= 0:
                self.game.winner = player.player
                self.game.status = 'finished'
                self.game.finished_at = timezone.now()
                self.game.save()
                return True
                
        return False
        
    def end_turn_and_switch_player(self):
        """Finaliza o turno e troca de jogador"""
        # Reseta ações
        self.player_game.actions_remaining = 3
        self.player_game.has_attacked = False
        self.player_game.save()
        
        # Próximo jogador
        if self.player_game.is_first_player:
            # Troca para o segundo jogador
            self.player_game = self._get_second_player()
        else:
            # Volta para o primeiro jogador
            self.player_game = self._get_first_player()
            
        # Atualiza turno
        self.player_game.turn_number += 1
        self.player_game.has_attacked = False
        self.player_game.save()
        
        # Gera fé para o novo turno
        self._generate_faith_for_next_turn()
        
        return self.player_game
        
    def perform_action(self, action_type, card=None, target=None):
        """Realiza uma ação no jogo"""
        if self.player_game.actions_remaining <= 0:
            return False, "Sem ações restantes"
            
        if action_type == 'play_card':
            if not self.can_play_card(card):
                return False, "Não é possível jogar esta carta"
            return self.play_card(card), "Carta jogada com sucesso"
            
        elif action_type == 'attack':
            if not self.player_game.has_attacked:
                if card and target:
                    attacker = PlayerBoardCard.objects.get(
                        player_game=self.player_game,
                        card=card
                    )
                    defender = PlayerBoardCard.objects.get(
                        player_game=target.player_game,
                        card=target.card
                    )
                    
                    # Calcula dano
                    damage = attacker.current_attack
                    defender.current_health -= damage
                    
                    # Verifica se a criatura morreu
                    if defender.current_health <= 0:
                        defender.delete()
                        
                    # Marca como tendo atacado
                    attacker.has_attacked = True
                    attacker.save()
                    
                    return True, f"Atacou! {defender.card.name} recebeu {damage} de dano"
                else:
                    return False, "Selecione uma carta e um alvo"
                    
        elif action_type == 'end_turn':
            return self.end_turn(), "Turno finalizado"
            
        return False, "Ação inválida"


# Helper functions
def create_new_deck(player, god_name, deck_name="My Deck"):
    """Cria um novo baralho para o jogador"""
    god = God.objects.get(name=god_name)
    deck = Deck.objects.create(owner=player, name=deck_name, god=god)
    return deck


def create_initial_deck(deck, god):
    """Cria um baralho inicial com 30 cartas"""
    # Este é um exemplo simplificado - em um jogo real, você precisaria de uma fonte de cartas
    # Para este protótipo, vamos criar cartas fictícias
    card_types = ['Monster', 'Spell', 'Relic']
    rarities = ['Common', 'Uncommon', 'Rare']
    
    # Cria cartas fictícias
    cards = []
    for i in range(30):
        card_type = random.choice(card_types)
        card_class = 'Neutral'  # Simplificação
        rarity = random.choice(rarities)
        cost = random.randint(0, 5)
        attack = random.randint(0, 5) if card_type == 'Monster' else 0
        health = random.randint(1, 8) if card_type == 'Monster' else 0
        description = f"{card_type} de nível {i+1}"
        
        card = Card.objects.create(
            name=f"Carta {i+1}",
            card_type=CardType.objects.get(name=card_type),
            rarity=Rarity.objects.get(name=rarity),
            cost=cost,
            attack=attack,
            health=health,
            description=description,
            card_class=CardClass.objects.get(name=card_class)
        )
        cards.append(card)
        
    # Adiciona ao deck
    for card in cards:
        deck.add_card(card)
        
    return deck.is_valid()


def validate_deck(deck):
    """Valida se o baralho tem pelo menos 20 cartas"""
    return deck.is_valid()