use crate::physical::{Grid, GridValue, Coordinate, Router, LeeRouter};

pub fn draw_grid(grid: &Grid) -> String {
    let mut output = String::new();

    output.push_str("\n┌─ Routing Grid ──────────────────────┐\n");
    output.push_str("│                                       │\n");

    let height = grid.height;
    let width = grid.width;

    for y in 0..height {
        let mut row = String::from("│ ");
        for x in 0..width {
            let cell = grid.get(x, y).unwrap_or(GridValue::Empty);
            let ch = match cell {
                GridValue::Empty => '·',
                GridValue::Obstacle => '▒',
                GridValue::Wire => '●',
                GridValue::Pin => '○',
            };
            row.push(ch);
        }
        row.push_str(" │");
        output.push_str(&row);
        output.push('\n');
    }

    output.push_str("│                                       │\n");
    output.push_str("├─ Legend ──────────────────────────────┤\n");
    output.push_str("│ · empty  ▒ obstacle  ● wire  ○ pin │\n");
    output.push_str("└───────────────────────────────────────┘\n");

    output
}

pub fn draw_grid_with_routes(grid: &Grid, routes: &[Vec<Coordinate>]) -> String {
    let mut output = String::new();

    output.push_str("\n╔════════════════════════════════════╗\n");
    output.push_str("║       Routing Visualization        ║\n");
    output.push_str("╠════════════════════════════════════╣\n");

    let mut display_grid = grid.cells.clone();

    let colors = ['1', '2', '3', '4', '5', '6'];

    for (i, route) in routes.iter().enumerate() {
        let color = colors[i % colors.len()];
        for &coord in route {
            let x = coord.x as usize;
            let y = coord.y as usize;
            if y < display_grid.len() && x < display_grid[0].len() {
                if display_grid[y][x] == GridValue::Empty {
                    display_grid[y][x] = GridValue::Wire;
                }
            }
        }
    }

    output.push_str("║\n");
    for y in 0..grid.height {
        let mut row = String::from("║ ");
        for x in 0..grid.width {
            let cell = &display_grid[y][x];
            let ch = match cell {
                GridValue::Empty => '·',
                GridValue::Obstacle => '▒',
                GridValue::Wire => '●',
                GridValue::Pin => '○',
            };
            row.push(ch);
        }
        row.push_str(" ║");
        output.push_str(&row);
        output.push('\n');
    }
    output.push_str("║\n");
    output.push_str("╠════════════════════════════════════╣\n");
    output.push_str("║ Legend: · empty  ▒ block  ● wire   ║\n");
    output.push_str("║           ○ pin                  ║\n");
    output.push_str("╠════════════════════════════════════╣\n");
    output.push_str(&format!("║ Routes found: \x1b[1;33m{}\x1b[0m                ║\n", routes.len()));

    for (i, route) in routes.iter().enumerate() {
        output.push_str(&format!("║ Route {}: {} segments           ║\n", i + 1, route.len()));
    }

    output.push_str("╚════════════════════════════════════╝\n");

    output
}

pub fn draw_route_path(grid: &Grid, start: Coordinate, end: Coordinate) -> String {
    let mut output = String::new();

    let mut router = LeeRouter::new();
    let route = router.route(grid, start, end);

    output.push_str("\n┌─ Lee's Algorithm Path ──────────────┐\n");
    output.push_str("│                                       │\n");

    let mut display_grid: Vec<Vec<char>> = (0..grid.height)
        .map(|_| (0..grid.width).map(|_| '·').collect())
        .collect();

    for y in 0..grid.height {
        for x in 0..grid.width {
            if let Some(cell) = grid.get(x, y) {
                display_grid[y][x] = match cell {
                    GridValue::Empty => '·',
                    GridValue::Obstacle => '█',
                    GridValue::Wire => '○',
                    GridValue::Pin => '●',
                };
            }
        }
    }

    if let Some(path) = &route {
        for &coord in path {
            let x = coord.x as usize;
            let y = coord.y as usize;
            if y < display_grid.len() && x < display_grid[0].len() {
                if display_grid[y][x] == '·' {
                    display_grid[y][x] = '○';
                }
            }
        }

        if let Some(first) = path.first() {
            let x = first.x as usize;
            let y = first.y as usize;
            if y < display_grid.len() && x < display_grid[0].len() {
                display_grid[y][x] = 'S';
            }
        }
        if let Some(last) = path.last() {
            let x = last.x as usize;
            let y = last.y as usize;
            if y < display_grid.len() && x < display_grid[0].len() {
                display_grid[y][x] = 'E';
            }
        }
    }

    for row in &display_grid {
        output.push_str(&format!("│ {}\n", row.iter().collect::<String>()));
    }

    output.push_str("│                                       │\n");
    output.push_str("├─ Legend ──────────────────────────────┤\n");
    output.push_str("│ · empty  █ block  ○ path             │\n");
    output.push_str("│ S start  E end                       │\n");
    output.push_str("└───────────────────────────────────────┘\n");

    if let Some(path) = route {
        output.push_str(&format!("\n\x1b[1;32mPath found!\x1b[0m {} steps\n", path.len()));
    } else {
        output.push_str("\n\x1b[1;31mNo path found!\x1b[0m\n");
    }

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_draw_grid() {
        let grid = Grid::new(10, 8);
        let output = draw_grid(&grid);
        assert!(!output.is_empty());
        assert!(output.contains("·"));
    }

    #[test]
    fn test_draw_grid_with_routes() {
        let mut grid = Grid::new(10, 10);
        grid.set_pin(0, 5);
        grid.set_pin(9, 5);

        let mut router = LeeRouter::new();
        let route = router.route(&grid, Coordinate::new(0, 5), Coordinate::new(9, 5));

        let routes = if let Some(r) = route {
            vec![r]
        } else {
            vec![]
        };

        let output = draw_grid_with_routes(&grid, &routes);
        assert!(!output.is_empty());
    }

    #[test]
    fn test_draw_route_path() {
        let mut grid = Grid::new(15, 10);
        grid.set_pin(0, 5);
        grid.set_pin(14, 5);

        let output = draw_route_path(&grid, Coordinate::new(0, 5), Coordinate::new(14, 5));
        assert!(!output.is_empty());
        assert!(output.contains("S"));
        assert!(output.contains("E"));
    }
}