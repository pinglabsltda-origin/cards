# Jogo de Cartas Olypus - Implementation Complete

## Overview
A complete card game built with Django following your specifications:

### Game Rules Implemented:
- **Victory Condition**: Reduce enemy Patron God HP from 30 to 0
- **Initial Life**: 30 PV for each Deus Patrono
- **Deck Size**: 30 cards maximum, 2 copies normal, 1 copy legendary
- **Mão Inicial**: 3 cartas (2º jogador: 4 + 1 carta temporária de Fé/Mana)
- **Limite de Campo**: 7 criaturas simultâneas
- **Recursos (Fé)**: Começa em 1 no turno 1, aumenta +1 a cada turno até 10
- **Máximo de cartas na mão**: 10

### Deities (4 Gods with exclusive mechanics):
1. **Zeus** (Controle) - Limpeza de mesa com feitiços, cartas ficam mais fortes após lançar magia
2. **Ares** (Aggro) - Foco em ataque rápido, armas que equipam no Deus, ímpeto das unidades
3. **Atena** (Midrange) - Exército fortalecido, bônus por criatura adjacente, bênção com Guardião
4. **Hades** (Sacrifício) - Mecânica de sacrifício próprio, efeitos ao morrer, reviver do cemitério

### Cards Created (10+):
- Hoplita Recruta, Sátiro Trapaceiro, Centauro Batedor, Ciclope Menor
- Raio do Olimpo, Oráculo de Delfos, Tempestade Implacável  
- Espartano Sanguinário, Lança de Esparta, Grito de Guerra Aresiano

### Technical Features:
- Django models for Gods, Cards, Decks, Game state
- Custom login/register system with Django authentication
- Drag-and-drop card playing (JavaScript frontend)
- AJAX API for card validation and execution
- Template inheritance with Tailwind-like custom CSS
- Admin panel registration for all models

### URLs:
- `/` - Home page
- `/mesa/` - Game board (after login)
- `/login/` - Login/Register system
- `/logout/` - Logout

The virtual environment is activated and the Django project is configured and ready to run.