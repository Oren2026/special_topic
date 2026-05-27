use crate::physical::{Placer, PlaceBlock, GridPlacer};

pub fn draw_placement(blocks: &[PlaceBlock], cols: usize) -> String {
    let mut output = String::new();

    if blocks.is_empty() {
        return "No blocks to draw\n".to_string();
    }

    let mut placer = GridPlacer::new(cols, 10.0);
    let mut blocks_clone = blocks.to_vec();
    placer.place(&mut blocks_clone);

    let scale = 3.0;
    let max_x = blocks_clone.iter().filter_map(|b| b.x.map(|x| x + b.width)).fold(60.0, f64::max);
    let max_y = blocks_clone.iter().filter_map(|b| b.y.map(|y| y + b.height)).fold(60.0, f64::max);

    let width = (max_x * scale) as usize + 4;
    let height = (max_y * scale) as usize + 4;

    let mut grid = vec![vec![' '; width]; height];

    for block in &blocks_clone {
        if let (Some(x), Some(y)) = (block.x, block.y) {
            let x1 = (x * scale) as usize;
            let y1 = (height - (y * scale) as usize) - 1;
            let bw = (block.width * scale) as usize;
            let bh = (block.height * scale) as usize;

            for dy in 0..bh {
                for dx in 0..bw {
                    let gy = y1.saturating_sub(dy);
                    let gx = x1.saturating_add(dx);
                    if gy < height && gx < width {
                        if dy == 0 || dy == bh - 1 || dx == 0 || dx == bw - 1 {
                            grid[gy][gx] = '█';
                        } else {
                            grid[gy][gx] = '░';
                        }
                    }
                }
            }

            let label = format!("{}", block.id);
            for (i, c) in label.chars().take(bw - 2).enumerate() {
                if y1.saturating_sub(bh / 2) < height && x1 + 1 + i < width {
                    grid[y1.saturating_sub(bh / 2)][x1 + 1 + i] = c;
                }
            }
        }
    }

    output.push_str("\n┌─ Placement ─────────────────────────┐\n");
    output.push_str("│                                       │\n");

    for row in &grid {
        output.push_str(&format!("│ {}\n", row.iter().collect::<String>()));
    }

    output.push_str("│                                       │\n");
    output.push_str("├─ Legend ──────────────────────────────┤\n");

    let mut ids: Vec<String> = blocks_clone.iter()
        .map(|b| format!("\x1b[1m{}\x1b[0m:{:?}x{:?}",
            b.id, b.width, b.height))
        .collect();
    ids.sort();

    for id in ids {
        output.push_str(&format!("│  {}                           │\n", id));
    }

    output.push_str("└───────────────────────────────────────┘\n");

    output
}

pub fn draw_placement_simple(blocks: &[PlaceBlock], cols: usize) -> String {
    let mut output = String::new();

    let mut placer = GridPlacer::new(cols, 10.0);
    let mut blocks_clone = blocks.to_vec();
    placer.place(&mut blocks_clone);

    output.push_str("\n╔════════════════════════════════════╗\n");
    output.push_str("║       Placement Visualization     ║\n");
    output.push_str("╠════════════════════════════════════╣\n");

    let scale = 3.0;
    let max_x = blocks_clone.iter().filter_map(|b| b.x.map(|x| x + b.width)).fold(60.0, f64::max);
    let max_y = blocks_clone.iter().filter_map(|b| b.y.map(|y| y + b.height)).fold(60.0, f64::max);

    let width = (max_x * scale) as usize + 4;
    let height = (max_y * scale) as usize + 4;

    let mut grid = vec![vec![' '; width]; height];

    let patterns = ['█', '▓', '▒', '░', '◫', '◧'];

    for (i, block) in blocks_clone.iter().enumerate() {
        if let (Some(x), Some(y)) = (block.x, block.y) {
            let x1 = (x * scale) as usize;
            let y1 = (height - (y * scale) as usize) - 1;
            let bw = (block.width * scale) as usize;
            let bh = (block.height * scale) as usize;
            let pattern = patterns[i % patterns.len()];

            for dy in 0..bh {
                for dx in 0..bw {
                    let gy = y1.saturating_sub(dy);
                    let gx = x1.saturating_add(dx);
                    if gy < height && gx < width {
                        grid[gy][gx] = pattern;
                    }
                }
            }
        }
    }

    output.push_str("║\n");
    for row in &grid {
        output.push_str(&format!("║ {}\n", row.iter().collect::<String>()));
    }
    output.push_str("║\n");
    output.push_str("╠════════════════════════════════════╣\n");

    for (i, block) in blocks_clone.iter().enumerate() {
        let color_code = 31 + (i % 6);
        output.push_str(&format!("║ \x1b[{}m■\x1b[0m Block{}: {:.1}x{:.1} at ({:.1},{:.1})\n",
            color_code, block.id, block.width, block.height,
            block.x.unwrap_or(0.0), block.y.unwrap_or(0.0)));
    }

    output.push_str("╚════════════════════════════════════╝\n");

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_draw_placement() {
        let blocks = vec![
            PlaceBlock::new(0, 15.0, 10.0),
            PlaceBlock::new(1, 10.0, 8.0),
            PlaceBlock::new(2, 12.0, 6.0),
        ];
        let output = draw_placement(&blocks, 2);
        assert!(!output.is_empty());
        assert!(output.contains("0"));
    }

    #[test]
    fn test_draw_placement_simple() {
        let blocks = vec![
            PlaceBlock::new(0, 20.0, 15.0),
            PlaceBlock::new(1, 10.0, 10.0),
        ];
        let output = draw_placement_simple(&blocks, 3);
        assert!(!output.is_empty());
        assert!(output.contains("Block0"));
    }
}