use crate::physical::{Floorplan, Block};

pub fn draw_floorplan(fp: &Floorplan) -> String {
    let mut output = String::new();

    let scale = 2.0;
    let width = ((fp.die.x2 - fp.die.x1) * scale) as usize;
    let height = ((fp.die.y2 - fp.die.y1) * scale) as usize;

    let mut grid = vec![vec![' '; width]; height];

    fn set_rect(grid: &mut Vec<Vec<char>>, x1: usize, y1: usize, x2: usize, y2: usize, ch: char) {
        for y in y1..y2.min(grid.len()) {
            for x in x1..x2.min(grid[0].len()) {
                grid[y][x] = ch;
            }
        }
    }

    let colors = ['░', '▒', '▓', '█', '◫', '◧', '◨', '◪'];

    for (i, block) in fp.blocks.iter().enumerate() {
        if let Some(rect) = block.rect() {
            let x1 = ((rect.x1 - fp.die.x1) * scale) as usize;
            let y1 = ((rect.y1 - fp.die.y1) * scale) as usize;
            let x2 = ((rect.x2 - fp.die.x1) * scale) as usize;
            let y2 = ((rect.y2 - fp.die.y1) * scale) as usize;

            let ch = colors[i % colors.len()];

            for y in y1.min(height)..y2.min(height) {
                for x in x1.min(width)..x2.min(width) {
                    grid[y][x] = ch;
                }
            }

            let name = &block.name;
            let name_len = name.len().min(x2.saturating_sub(x1) - 2);
            let start_x = x1 + 1;

            for (i, c) in name.chars().take(name_len).enumerate() {
                if y1 + 1 < height && start_x + i < width {
                    grid[y1 + 1][start_x + i] = c;
                }
            }
        }
    }

    let border_char = '─';
    let corner_char = '┼';

    output.push_str(&format!("┌{}┐\n", border_char.to_string().repeat(width + 2)));

    for row in &grid {
        output.push_str(&format!("│ {}", row.iter().collect::<String>()));
        output.push_str(" │\n");
    }

    output.push_str(&format!("└{}┘\n", border_char.to_string().repeat(width + 2)));

    output.push_str(&format!("\n\x1b[1;36mDie Size:\x1b[0m {:.1} x {:.1}\n",
        fp.die.width(), fp.die.height()));
    output.push_str(&format!("\x1b[1;36mBlocks:\x1b[0m\n"));
    for block in &fp.blocks {
        if let Some(rect) = block.rect() {
            output.push_str(&format!("  {}: {:.1}x{:.1} at ({:.1},{:.1})\n",
                block.name, block.width, block.height, rect.x1, rect.y1));
        }
    }

    if !fp.nets.is_empty() {
        output.push_str(&format!("\x1b[1;36mNets:\x1b[0m {} connections\n", fp.nets.len()));
    }

    let wl = fp.hpwl();
    output.push_str(&format!("\x1b[1;33mHPWL:\x1b[0m {:.2}\n", wl));

    output
}

pub fn draw_floorplan_simple(fp: &Floorplan) -> String {
    let mut output = String::new();

    output.push_str("\n╔══════════════════════════════════════╗\n");
    output.push_str("║       Floorplanning Visualization    ║\n");
    output.push_str("╠══════════════════════════════════════╣\n");

    let scale = 3.0;
    let width = ((fp.die.x2 - fp.die.x1) * scale) as usize;
    let height = ((fp.die.y2 - fp.die.y1) * scale) as usize;

    let mut grid = vec![vec![' '; width]; height];

    let blocks_sorted: Vec<&Block> = fp.blocks.iter().filter(|b| b.rect().is_some()).collect();

    for (i, block) in blocks_sorted.iter().enumerate() {
        if let Some(rect) = block.rect() {
            let x1 = ((rect.x1 - fp.die.x1) * scale) as usize;
            let y1 = ((rect.y1 - fp.die.y1) * scale) as usize;
            let bw = (block.width * scale) as usize;
            let bh = (block.height * scale) as usize;

            let pattern = match i % 4 {
                0 => '█',
                1 => '▓',
                2 => '▒',
                _ => '░',
            };

            for y in y1..(y1 + bh).min(height) {
                for x in x1..(x1 + bw).min(width) {
                    grid[y][x] = pattern;
                }
            }
        }
    }

    output.push_str("║\n");
    for row in &grid {
        output.push_str(&format!("║ {}\n", row.iter().collect::<String>()));
    }
    output.push_str("║\n");

    output.push_str("╠══════════════════════════════════════╣\n");

    let mut block_info = String::new();
    for (i, block) in blocks_sorted.iter().enumerate() {
        if let Some(rect) = block.rect() {
            block_info.push_str(&format!("  \x1b[{}m■\x1b[0m {}: {:.0}x{:.0} at ({:.0},{:.0})\n",
                31 + (i % 6), block.name, block.width, block.height, rect.x1, rect.y1));
        }
    }

    output.push_str(&block_info);

    let wl = fp.hpwl();
    output.push_str(&format!("╠══════════════════════════════════════╣\n"));
    output.push_str(&format!("║ HPWL: \x1b[1;33m{:.2}\x1b[0m                         ║\n", wl));
    output.push_str("╚══════════════════════════════════════╝\n");

    output
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Rect;

    #[test]
    fn test_draw_floorplan_simple() {
        let die = Rect::new(0.0, 0.0, 60.0, 40.0);
        let mut fp = Floorplan::new(die);
        fp.add_block(Block::new(0, "CPU", 30.0, 20.0));
        fp.add_block(Block::new(1, "ALU", 15.0, 15.0));
        fp.blocks[0].x = Some(0.0);
        fp.blocks[0].y = Some(0.0);
        fp.blocks[1].x = Some(35.0);
        fp.blocks[1].y = Some(0.0);

        let output = draw_floorplan_simple(&fp);
        assert!(!output.is_empty());
        assert!(output.contains("CPU"));
    }

    #[test]
    fn test_draw_floorplan() {
        let die = Rect::new(0.0, 0.0, 50.0, 50.0);
        let mut fp = Floorplan::new(die);
        fp.add_block(Block::new(0, "A", 20.0, 20.0));
        fp.blocks[0].x = Some(0.0);
        fp.blocks[0].y = Some(0.0);

        let output = draw_floorplan(&fp);
        assert!(!output.is_empty());
        assert!(output.contains("A"));
    }
}