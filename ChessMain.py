"""
Main driver file.
Handling user input.
Displaying current GameStatus object.
"""
# if os.name == 'nt':  # Windows
#     sys.stdout = open('nul', 'w')

import pygame as p
import chess
import chess.engine
import ChessEngine, ChessAI
import sys
from multiprocessing import Process, Queue
from main_screen import main_screen
from end_screen import end_screen  # Import the end_screen function

BOARD_WIDTH = 512
BOARD_HEIGHT = 512
MOVE_LOG_PANEL_WIDTH = 250
MOVE_LOG_PANEL_HEIGHT = BOARD_HEIGHT
DIMENSION = 8
SQUARE_SIZE = BOARD_HEIGHT // DIMENSION
EVAL_BAR_WIDTH = 15  # New constant for the evaluation bar width
MAX_FPS = 15
IMAGES = {}


def loadImages():
    """
    Initialize a global directory of images.
    This will be called exactly once in the main.
    """
    pieces = ['wp', 'wR', 'wN', 'wB', 'wK', 'wQ', 'bp', 'bR', 'bN', 'bB', 'bK', 'bQ']
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load("images/" + piece + ".png"), (SQUARE_SIZE, SQUARE_SIZE))


def main():
    """
    The main driver for our code.
    This will handle user input and updating the graphics.
    """
    if not p.get_init():
        p.init()
    screen = p.display.set_mode((BOARD_WIDTH + EVAL_BAR_WIDTH + MOVE_LOG_PANEL_WIDTH, BOARD_HEIGHT))
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    game_state = ChessEngine.GameState()
    valid_moves = game_state.getValidMoves()
    move_made = False  # flag variable for when a move is made
    animate = False  # flag variable for when we should animate a move
    loadImages()  # do this only once before while loop
    running = True
    square_selected = ()  # no square is selected initially, this will keep track of the last click of the user (tuple(row,col))
    player_clicks = []  # this will keep track of player clicks (two tuples)
    game_over = False
    ai_thinking = False
    move_undone = False
    move_finder_process = None
    move_log_font = p.font.SysFont("Arial", 14, False, False)
    engine = chess.engine.SimpleEngine.popen_uci("C:/Users/abhin/Just for fun/chessai/stockfish/stockfish-windows-x86-64-avx2.exe")
    player_choice = main_screen()
    
    if player_choice is None:
        # User closed the window without making a choice, exit the game
        return
    
    # Set player_one and player_two based on player's choice
    if player_choice == "ai":
        player_one = True
        player_two = False
    else:
        player_one = True
        player_two = True

    while running:
        human_turn = (game_state.white_to_move and player_one) or (not game_state.white_to_move and player_two)
        for e in p.event.get():
            if e.type == p.QUIT:
                print("Quit event detected")
                running = False
                p.quit()
                sys.exit()
            # mouse handler
            elif e.type == p.MOUSEBUTTONDOWN:
                if not game_over:
                    location = p.mouse.get_pos()  # (x, y) location of the mouse
                    col = location[0] // SQUARE_SIZE
                    row = location[1] // SQUARE_SIZE
                    if square_selected == (row, col) or col >= 8:  # user clicked the same square twice
                        square_selected = ()  # deselect
                        player_clicks = []  # clear clicks
                    else:
                        square_selected = (row, col)
                        player_clicks.append(square_selected)  # append for both 1st and 2nd click
                    if len(player_clicks) == 2 and human_turn:  # after 2nd click
                        move = ChessEngine.Move(player_clicks[0], player_clicks[1], game_state.board)
                        for i in range(len(valid_moves)):
                            if move == valid_moves[i]:
                                game_state.makeMove(valid_moves[i])
                                move_made = True
                                animate = True
                                square_selected = ()  # reset user clicks
                                player_clicks = []
                        if not move_made:
                            player_clicks = [square_selected]

            # key handler
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:  # undo when 'z' is pressed
                    game_state.undoMove()
                    move_made = True
                    animate = False
                    game_over = False
                    if ai_thinking:
                        move_finder_process.terminate()
                        ai_thinking = False
                    move_undone = True
                if e.key == p.K_r:  # reset the game when 'r' is pressed
                    game_state = ChessEngine.GameState()
                    valid_moves = game_state.getValidMoves()
                    square_selected = ()
                    player_clicks = []
                    move_made = False
                    animate = False
                    game_over = False
                    if ai_thinking:
                        move_finder_process.terminate()
                        ai_thinking = False
                    move_undone = True

        # AI move finder
        if not game_over and not human_turn and not move_undone:
            if not ai_thinking:
                ai_thinking = True
                return_queue = Queue()  # used to pass data between threads
                move_finder_process = Process(target=ChessAI.findBestMove, args=(game_state, valid_moves, return_queue))
                move_finder_process.start()

            if not move_finder_process.is_alive():
                ai_move = return_queue.get()
                if ai_move is None:
                    ai_move = ChessAI.findRandomMove(valid_moves)
                game_state.makeMove(ai_move)
                move_made = True
                animate = True
                ai_thinking = False

        if move_made:
            if animate:
                animateMove(game_state.move_log[-1], screen, game_state.board, clock)
            valid_moves = game_state.getValidMoves()
            move_made = False
            animate = False
            move_undone = False
        
        # Get the Stockfish move
        board = chess.Board(game_state.fen())  # Convert game_state to a python-chess Board object
        stockfish_move = engine.play(board, chess.engine.Limit(time=0.1)).move  # Get Stockfish's move

        drawGameState(screen, game_state, valid_moves, square_selected)

        if not game_over:
            drawMoveLog(screen, game_state, move_log_font, stockfish_move)

        if game_state.checkmate or game_state.stalemate:
            game_over = True
            result = "Checkmate" if game_state.checkmate else "Stalemate"
            drawEndGameText(screen, f"{result}!")

            # Print the move log to the console
            print(f"Game Over - {result}!")
            printMoveLogAsPGN(game_state.move_log)

            play_again = end_screen(result)
            if play_again:
                player_choice = main_screen()
                if player_choice is not None:
                    # Reset the game state and continue the game loop
                    game_state = ChessEngine.GameState()
                    valid_moves = game_state.getValidMoves()
                    square_selected = ()
                    player_clicks = []
                    move_made = False
                    animate = False
                    game_over = False
                    if player_choice == "ai":
                        player_one = True
                        player_two = False
                    else:
                        player_one = True
                        player_two = True
            else:
                running = False

        clock.tick(MAX_FPS)
        p.display.flip()

    engine.quit()
    p.quit()
    
    
def drawGameState(screen, game_state, valid_moves, square_selected):
    """
    Responsible for all the graphics within current game state.
    """
    drawBoard(screen)  # draw squares on the board
    highlightSquares(screen, game_state, valid_moves, square_selected)
    drawPieces(screen, game_state.board)  # draw pieces on top of those squares
    
    # Draw evaluation bar
    evaluation_bar_width = EVAL_BAR_WIDTH
    evaluation_bar_height = BOARD_HEIGHT
    evaluation_bar_rect = p.Rect(BOARD_WIDTH, 0, evaluation_bar_width, evaluation_bar_height)
    p.draw.rect(screen, p.Color('gray'), evaluation_bar_rect)

    # Get Stockfish's evaluation of the current position
    engine = chess.engine.SimpleEngine.popen_uci("C:/Users/abhin/Just for fun/chessai/stockfish/stockfish-windows-x86-64-avx2.exe")
    board = chess.Board(game_state.fen())
    info = engine.analyse(board, chess.engine.Limit(depth=10))
    evaluation = info["score"].white().score(mate_score=32000)
    
    # Draw evaluation score# Draw evaluation score with a smaller font size
    font = p.font.SysFont(None, 18)  # Smaller font size to fit within the designated area
    score_text = f"Eval:\n{evaluation / 100:.2f}"  # Shorter text
    text_obj = font.render(score_text, True, p.Color('white'))

    # Adjust the position of the text to ensure it fits
    text_rect = text_obj.get_rect()
    text_rect.center = (BOARD_WIDTH + EVAL_BAR_WIDTH // 2, 10)  # Centered horizontally
    screen.blit(text_obj, text_rect)
    
    # Calculate the height for the white advantage bar
    if evaluation >= 0:  
        # Convert the evaluation score to a proportional height
        bar_height = (evaluation + 32000) / 64000 * evaluation_bar_height
        bar_rect = p.Rect(BOARD_WIDTH, evaluation_bar_height - bar_height, evaluation_bar_width, bar_height)
        bar_color = (0, 255, 0)  # Green for White's advantage
        p.draw.rect(screen, bar_color, bar_rect)
    else:  # If Black has the advantage, the green bar is smaller, emphasizing more gray
        # Proportional height when Black has an advantage (inverted)
        bar_height = (32000 - abs(evaluation)) / 64000 * evaluation_bar_height
        # Draw the reduced green bar for Black's advantage
        bar_rect = p.Rect(BOARD_WIDTH, evaluation_bar_height - bar_height, evaluation_bar_width, bar_height)
        p.draw.rect(screen, (0, 255, 0), bar_rect)
    
    engine.quit()

def drawBoard(screen):
    """
    Draw the squares on the board.
    The top left square is always light.
    """
    global colors
    colors = [p.Color("white"), p.Color("teal")]
    for row in range(DIMENSION):
        for column in range(DIMENSION):
            color = colors[((row + column) % 2)]
            p.draw.rect(screen, color, p.Rect(column * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))


def highlightSquares(screen, game_state, valid_moves, square_selected):
    """
    Highlight square selected and moves for piece selected.
    """
    if (len(game_state.move_log)) > 0:
        last_move = game_state.move_log[-1]
        s = p.Surface((SQUARE_SIZE, SQUARE_SIZE))
        s.set_alpha(100)
        s.fill(p.Color('green'))
        screen.blit(s, (last_move.end_col * SQUARE_SIZE, last_move.end_row * SQUARE_SIZE))
    if square_selected != ():
        row, col = square_selected
        if game_state.board[row][col][0] == (
                'w' if game_state.white_to_move else 'b'):  # square_selected is a piece that can be moved
            # highlight selected square
            s = p.Surface((SQUARE_SIZE, SQUARE_SIZE))
            s.set_alpha(100)  # transparency value 0 -> transparent, 255 -> opaque
            s.fill(p.Color('blue'))
            screen.blit(s, (col * SQUARE_SIZE, row * SQUARE_SIZE))
            # highlight moves from that square
            s.fill(p.Color('yellow'))
            for move in valid_moves:
                if move.start_row == row and move.start_col == col:
                    screen.blit(s, (move.end_col * SQUARE_SIZE, move.end_row * SQUARE_SIZE))


def drawPieces(screen, board):
    """
    Draw the pieces on the board using the current game_state.board
    """
    for row in range(board.shape[0]):
        for col in range(board.shape[1]):
            piece = board[row, col]
            if piece != "--":
                screen.blit(IMAGES[piece], p.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def printMoveLogAsPGN(move_log):
    # Basic PGN setup
    pgn_output = []

    # Example metadata (you can customize this)
    pgn_output.append("[Event \"Chess Game\"]")
    pgn_output.append("[Site \"Local\"]")
    pgn_output.append("[Date \"2023.01.01\"]")
    pgn_output.append("[Round \"1\"]")
    pgn_output.append("[White \"Player1\"]")
    pgn_output.append("[Black \"Player2\"]")
    pgn_output.append("[Result \"*\"]")

    # Build the PGN moves
    turn_number = 1
    for i in range(0, len(move_log), 2):
        white_move = str(move_log[i])
        black_move = ""
        if i + 1 < len(move_log):
            black_move = str(move_log[i + 1])
        
        # Create the PGN move entry
        turn_entry = f"{turn_number}. {white_move} {black_move}"
        pgn_output.append(turn_entry)
        turn_number += 1

    # Add game result, if known (e.g., 1-0 for White win, 0-1 for Black win, 1/2-1/2 for draw)
    pgn_output.append("*")  # This indicates an undecided result

    # Print the PGN
    print("\n".join(pgn_output))

        
        
def drawMoveLog(screen, game_state, font, stockfish_move=None):
    move_log_rect = p.Rect(BOARD_WIDTH + EVAL_BAR_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, MOVE_LOG_PANEL_HEIGHT)
    p.draw.rect(screen, p.Color('black'), move_log_rect)
    move_log = game_state.move_log
    move_texts = []
    for i in range(0, len(move_log), 2):
        move_string = str(i // 2 + 1) + '. ' + str(move_log[i]) + " "
        if i + 1 < len(move_log):
            move_string += str(move_log[i + 1]) + "  "
        move_texts.append(move_string)

    moves_per_row = 3
    padding = 5
    line_spacing = 2
    text_y = padding
    for i in range(0, len(move_texts), moves_per_row):
        text = ""
        for j in range(moves_per_row):
            if i + j < len(move_texts):
                text += move_texts[i + j]

        text_object = font.render(text, True, p.Color('white'))
        text_location = move_log_rect.move(padding, text_y)
        screen.blit(text_object, text_location)
        text_y += text_object.get_height() + line_spacing

    # Draw Stockfish's suggested move
    if stockfish_move:
        board = chess.Board(game_state.fen())  # Convert game_state to a python-chess Board object
        stockfish_move_text = "Stockfish's move: " + board.san(stockfish_move)
        text_object = font.render(stockfish_move_text, True, p.Color('white'))
        text_location = move_log_rect.move(padding, MOVE_LOG_PANEL_HEIGHT - text_object.get_height() - padding)
        screen.blit(text_object, text_location)


def drawEndGameText(screen, text):
    font = p.font.SysFont("Helvetica", 32, True, False)
    text_object = font.render(text, False, p.Color("gray"))
    text_location = p.Rect(0, 0, BOARD_WIDTH, BOARD_HEIGHT).move(BOARD_WIDTH / 2 - text_object.get_width() / 2,
                                                                 BOARD_HEIGHT / 2 - text_object.get_height() / 2)
    screen.blit(text_object, text_location)
    text_object = font.render(text, False, p.Color('black'))
    screen.blit(text_object, text_location.move(2, 2))


def animateMove(move, screen, board, clock):
    """
    Animating a move
    """
    global colors
    d_row = move.end_row - move.start_row
    d_col = move.end_col - move.start_col
    frames_per_square = 10  # frames to move one square
    frame_count = (abs(d_row) + abs(d_col)) * frames_per_square
    for frame in range(frame_count + 1):
        row, col = (move.start_row + d_row * frame / frame_count, move.start_col + d_col * frame / frame_count)
        drawBoard(screen)
        drawPieces(screen, board)
        # erase the piece moved from its ending square
        color = colors[(move.end_row + move.end_col) % 2]
        end_square = p.Rect(move.end_col * SQUARE_SIZE, move.end_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        p.draw.rect(screen, color, end_square)
        # draw captured piece onto rectangle
        if move.piece_captured != '--':
            if move.is_enpassant_move:
                enpassant_row = move.end_row + 1 if move.piece_captured[0] == 'b' else move.end_row - 1
                end_square = p.Rect(move.end_col * SQUARE_SIZE, enpassant_row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            screen.blit(IMAGES[move.piece_captured], end_square)
        # draw moving piece
        screen.blit(IMAGES[move.piece_moved], p.Rect(col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))
        p.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()