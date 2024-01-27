from pygamejr import game

game.start()

triangle = game.create_polygon_any([(50,50), (20, 150), (80, 150)], color="green")

while game.is_running():
    triangle.turn_to(game.mouse_xy())
    triangle.glide_to(game.mouse_xy(), speed=2)

    if triangle.touches(game.mouse_xy()):
        triangle.add_text("boom", "BOOM!!")
    else:
        triangle.remove_text("boom")

    game.update()