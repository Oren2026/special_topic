use std::collections::HashMap;
use super::{Point, Rect};

pub trait Placer {
    fn place(&mut self, blocks: &mut [PlaceBlock]);
}

#[derive(Debug, Clone)]
pub struct PlaceBlock {
    pub id: usize,
    pub width: f64,
    pub height: f64,
    pub x: Option<f64>,
    pub y: Option<f64>,
    pub fixed: bool,
}

impl PlaceBlock {
    pub fn new(id: usize, width: f64, height: f64) -> Self {
        PlaceBlock {
            id,
            width,
            height,
            x: None,
            y: None,
            fixed: false,
        }
    }

    pub fn fixed(id: usize, width: f64, height: f64, x: f64, y: f64) -> Self {
        PlaceBlock {
            id,
            width,
            height,
            x: Some(x),
            y: Some(y),
            fixed: true,
        }
    }

    pub fn rect(&self) -> Option<Rect> {
        match (self.x, self.y) {
            (Some(x), Some(y)) => Some(Rect::new(x, y, x + self.width, y + self.height)),
            _ => None,
        }
    }
}

pub struct GridPlacer {
    pub cols: usize,
    pub row_height: f64,
}

impl GridPlacer {
    pub fn new(cols: usize, row_height: f64) -> Self {
        GridPlacer { cols, row_height }
    }
}

impl Placer for GridPlacer {
    fn place(&mut self, blocks: &mut [PlaceBlock]) {
        let mut x = 0.0;
        let mut y = 0.0;
        let mut max_h_in_row: f64 = 0.0;
        let mut col = 0;

        for block in blocks.iter_mut().filter(|b| !b.fixed) {
            block.x = Some(x);
            block.y = Some(y);
            max_h_in_row = max_h_in_row.max(block.height);
            x += block.width;
            col += 1;

            if col >= self.cols {
                col = 0;
                x = 0.0;
                y += max_h_in_row;
                max_h_in_row = 0.0;
            }
        }
    }
}

pub struct ForceDirectPlacer {
    pub spring_k: f64,
    pub damping: f64,
    pub iterations: usize,
}

impl ForceDirectPlacer {
    pub fn new() -> Self {
        ForceDirectPlacer {
            spring_k: 1.0,
            damping: 0.5,
            iterations: 100,
        }
    }

    fn calc_force(&self, blocks: &[PlaceBlock], netlist: &HashMap<usize, Vec<usize>>) -> HashMap<usize, Point> {
        let mut forces: HashMap<usize, Point> = HashMap::new();

        for block in blocks {
            let mut fx = 0.0;
            let mut fy = 0.0;

            if let Some(rect) = block.rect() {
                let cx = rect.center().x;
                let cy = rect.center().y;

                for other in blocks {
                    if other.id == block.id { continue; }
                    if let Some(other_rect) = other.rect() {
                        let dx = cx - other_rect.center().x;
                        let dy = cy - other_rect.center().y;
                        let dist = (dx * dx + dy * dy).sqrt().max(0.1);
                        let repulsion = 100.0 / (dist * dist);
                        fx += (dx / dist) * repulsion;
                        fy += (dy / dist) * repulsion;
                    }
                }
            }

            if let Some(connections) = netlist.get(&block.id) {
                for &other_id in connections {
                    if let Some(other) = blocks.iter().find(|b| b.id == other_id) {
                        if let (Some(r1), Some(r2)) = (block.rect(), other.rect()) {
                            let dx = r2.center().x - r1.center().x;
                            let dy = r2.center().y - r1.center().y;
                            fx += self.spring_k * dx;
                            fy += self.spring_k * dy;
                        }
                    }
                }
            }

            forces.insert(block.id, Point::new(fx, fy));
        }

        forces
    }
}

impl Default for ForceDirectPlacer {
    fn default() -> Self {
        Self::new()
    }
}

impl Placer for ForceDirectPlacer {
    fn place(&mut self, blocks: &mut [PlaceBlock]) {
        let mut netlist: HashMap<usize, Vec<usize>> = HashMap::new();
        for (i, block) in blocks.iter().enumerate() {
            if i + 1 < blocks.len() {
                netlist.entry(block.id).or_default().push(blocks[i + 1].id);
            }
        }

        for _ in 0..self.iterations {
            let forces = self.calc_force(blocks, &netlist);

            for block in blocks.iter_mut().filter(|b| !b.fixed) {
                if let Some(force) = forces.get(&block.id) {
                    if let (Some(x), Some(y)) = (block.x, block.y) {
                        block.x = Some(x + force.x * self.damping);
                        block.y = Some(y + force.y * self.damping);
                    } else {
                        block.x = Some(force.x * 10.0);
                        block.y = Some(force.y * 10.0);
                    }
                }
            }
        }
    }
}

pub struct CheckerboardPlacer {
    pub site_width: f64,
    pub site_height: f64,
}

impl CheckerboardPlacer {
    pub fn new(site_width: f64, site_height: f64) -> Self {
        CheckerboardPlacer { site_width, site_height }
    }

    pub fn place_grid(&self, blocks: &mut [PlaceBlock], cols: usize) {
        let mut col = 0;
        let mut row = 0;

        for block in blocks.iter_mut().filter(|b| !b.fixed) {
            block.x = Some(col as f64 * self.site_width);
            block.y = Some(row as f64 * self.site_height);

            col += (block.width / self.site_width).ceil() as usize;
            if col >= cols {
                col = 0;
                row += 1;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_place_block_new() {
        let b = PlaceBlock::new(0, 10.0, 5.0);
        assert_eq!(b.id, 0);
        assert_eq!(b.width, 10.0);
        assert!(!b.fixed);
    }

    #[test]
    fn test_place_block_fixed() {
        let b = PlaceBlock::fixed(0, 10.0, 5.0, 20.0, 30.0);
        assert!(b.fixed);
        assert_eq!(b.x, Some(20.0));
        assert_eq!(b.y, Some(30.0));
    }

    #[test]
    fn test_grid_placer() {
        let mut placer = GridPlacer::new(3, 10.0);
        let mut blocks = vec![
            PlaceBlock::new(0, 10.0, 5.0),
            PlaceBlock::new(1, 15.0, 5.0),
            PlaceBlock::new(2, 20.0, 5.0),
        ];
        placer.place(&mut blocks);

        assert!(blocks[0].x.is_some());
        assert!(blocks[0].y.is_some());
    }

    #[test]
    fn test_force_direct_placer() {
        let mut placer = ForceDirectPlacer::new();
        let mut blocks = vec![
            PlaceBlock::new(0, 10.0, 5.0),
            PlaceBlock::new(1, 10.0, 5.0),
        ];
        placer.place(&mut blocks);

        assert!(blocks[0].x.is_some());
        assert!(blocks[0].y.is_some());
    }

    #[test]
    fn test_checkerboard_placer() {
        let placer = CheckerboardPlacer::new(1.0, 1.0);
        let mut blocks = vec![
            PlaceBlock::new(0, 2.0, 1.0),
            PlaceBlock::new(1, 3.0, 1.0),
        ];
        placer.place_grid(&mut blocks, 10);

        assert!(blocks[0].x.is_some());
        assert!(blocks[0].y.is_some());
    }
}