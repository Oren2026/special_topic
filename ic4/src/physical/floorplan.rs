use rand::Rng;

#[derive(Debug, Clone)]
pub struct Block {
    pub id: usize,
    pub name: String,
    pub width: f64,
    pub height: f64,
    pub x: Option<f64>,
    pub y: Option<f64>,
}

impl Block {
    pub fn new(id: usize, name: &str, width: f64, height: f64) -> Self {
        Block {
            id,
            name: name.to_string(),
            width,
            height,
            x: None,
            y: None,
        }
    }

    pub fn rect(&self) -> Option<crate::Rect> {
        match (self.x, self.y) {
            (Some(x), Some(y)) => Some(crate::Rect::new(x, y, x + self.width, y + self.height)),
            _ => None,
        }
    }

    pub fn area(&self) -> f64 {
        self.width * self.height
    }

    pub fn aspect_ratio(&self) -> f64 {
        self.height / self.width
    }
}

pub enum Wirelength {
    HalfPerimeter,
    Steiner,
    BoundingBox,
}

pub struct Floorplan {
    pub blocks: Vec<Block>,
    pub nets: Vec<Net>,
    pub die: crate::Rect,
}

#[derive(Debug, Clone)]
pub struct Net {
    pub id: usize,
    pub connections: Vec<usize>,
}

impl Floorplan {
    pub fn new(die: crate::Rect) -> Self {
        Floorplan {
            blocks: Vec::new(),
            nets: Vec::new(),
            die,
        }
    }

    pub fn add_block(&mut self, block: Block) {
        self.blocks.push(block);
    }

    pub fn add_net(&mut self, connections: Vec<usize>) {
        let id = self.nets.len();
        self.nets.push(Net { id, connections });
    }

    pub fn calc_wirelength(&self, wl_type: Wirelength) -> f64 {
        match wl_type {
            Wirelength::HalfPerimeter => self.hpwl(),
            Wirelength::BoundingBox => self.bounding_box_wl(),
            Wirelength::Steiner => self.steiner_approx(),
        }
    }

    pub fn hpwl(&self) -> f64 {
        let mut total = 0.0;
        for net in &self.nets {
            if net.connections.len() < 2 { continue; }
            let mut min_x = f64::MAX;
            let mut min_y = f64::MAX;
            let mut max_x = f64::MIN;
            let mut max_y = f64::MIN;

            for &bid in &net.connections {
                if let Some(rect) = self.blocks.get(bid).and_then(|b| b.rect()) {
                    min_x = min_x.min(rect.x1);
                    min_y = min_y.min(rect.y1);
                    max_x = max_x.max(rect.x2);
                    max_y = max_y.max(rect.y2);
                }
            }

            if min_x != f64::MAX {
                total += (max_x - min_x) + (max_y - min_y);
            }
        }
        total
    }

    fn bounding_box_wl(&self) -> f64 {
        self.hpwl()
    }

    fn steiner_approx(&self) -> f64 {
        self.hpwl() * 1.1
    }

    pub fn calc_cost(&self, alpha: f64) -> f64 {
        let total_area: f64 = self.blocks.iter().map(|b| b.area()).sum();

        let wl = self.calc_wirelength(Wirelength::HalfPerimeter);

        alpha * wl + (1.0 - alpha) * total_area
    }

    pub fn pack_slicing(&mut self) {
        let mut x = self.die.x1;
        let mut y = self.die.y1;
        let mut max_h: f64 = 0.0;

        for block in &mut self.blocks {
            block.x = Some(x);
            block.y = Some(y);
            x += block.width;
            max_h = max_h.max(block.height);
            if x > self.die.x2 {
                x = self.die.x1;
                y += max_h;
                max_h = 0.0;
            }
        }
    }

    pub fn pack_bbtree(&mut self) {
        if self.blocks.is_empty() {
            return;
        }

        if self.blocks.len() == 1 {
            self.blocks[0].x = Some(self.die.x1);
            self.blocks[0].y = Some(self.die.y1);
            return;
        }

        let total_area: f64 = self.blocks.iter().map(|b| b.area()).sum();
        let ratio = (total_area / self.die.area()).sqrt();

        let width = self.die.width() * ratio.min(1.0);

        let mut x = self.die.x1;
        let mut y = self.die.y1;
        let mut current_row_max_h: f64 = 0.0;

        for block in &mut self.blocks {
            if x + block.width > self.die.x1 + width {
                x = self.die.x1;
                y += current_row_max_h;
                current_row_max_h = 0.0;
            }
            block.x = Some(x);
            block.y = Some(y);
            x += block.width;
            current_row_max_h = current_row_max_h.max(block.height);
        }
    }
}

pub struct SimulatedAnnealing {
    pub initial_temp: f64,
    pub final_temp: f64,
    pub cooling_rate: f64,
    pub iterations: usize,
}

impl SimulatedAnnealing {
    pub fn new() -> Self {
        SimulatedAnnealing {
            initial_temp: 10000.0,
            final_temp: 0.001,
            cooling_rate: 0.95,
            iterations: 1000,
        }
    }

    pub fn optimize(&self, floorplan: &mut Floorplan, alpha: f64) {
        let mut rng = rand::thread_rng();
        let mut current_cost = floorplan.calc_cost(alpha);
        let mut temperature = self.initial_temp;

        while temperature > self.final_temp {
            for _ in 0..self.iterations {
                let i = rng.gen_range(0..floorplan.blocks.len());
                let j = rng.gen_range(0..floorplan.blocks.len());

                if i != j {
                    let old_positions: Vec<(f64, f64)> = floorplan.blocks.iter()
                        .map(|b| (b.x.unwrap_or(0.0), b.y.unwrap_or(0.0)))
                        .collect();

                    floorplan.blocks[i].x = Some(rng.gen_range(floorplan.die.x1..floorplan.die.x2));
                    floorplan.blocks[i].y = Some(rng.gen_range(floorplan.die.y1..floorplan.die.y2));

                    let new_cost = floorplan.calc_cost(alpha);
                    let delta = new_cost - current_cost;

                    if delta < 0.0 || rng.gen::<f64>() < (-delta / temperature).exp() {
                        current_cost = new_cost;
                    } else {
                        for (k, block) in floorplan.blocks.iter_mut().enumerate() {
                            block.x = Some(old_positions[k].0);
                            block.y = Some(old_positions[k].1);
                        }
                    }
                }
            }
            temperature *= self.cooling_rate;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_area() {
        let b = Block::new(0, "test", 10.0, 5.0);
        assert_eq!(b.area(), 50.0);
    }

    #[test]
    fn test_block_aspect_ratio() {
        let b = Block::new(0, "test", 2.0, 4.0);
        assert_eq!(b.aspect_ratio(), 2.0);
    }

    #[test]
    fn test_floorplan_creation() {
        let die = crate::Rect::new(0.0, 0.0, 100.0, 100.0);
        let fp = Floorplan::new(die);
        assert!(fp.blocks.is_empty());
    }

    #[test]
    fn test_add_block() {
        let die = crate::Rect::new(0.0, 0.0, 100.0, 100.0);
        let mut fp = Floorplan::new(die);
        fp.add_block(Block::new(0, "B1", 10.0, 10.0));
        assert_eq!(fp.blocks.len(), 1);
    }

    #[test]
    fn test_pack_slicing() {
        let die = crate::Rect::new(0.0, 0.0, 100.0, 100.0);
        let mut fp = Floorplan::new(die);
        fp.add_block(Block::new(0, "B1", 20.0, 10.0));
        fp.add_block(Block::new(1, "B2", 15.0, 10.0));
        fp.pack_slicing();

        if let Some(rect) = fp.blocks[0].rect() {
            assert!(rect.x1 >= 0.0);
        }
    }

    #[test]
    fn test_hpwl() {
        let die = crate::Rect::new(0.0, 0.0, 100.0, 100.0);
        let mut fp = Floorplan::new(die);
        fp.add_block(Block::new(0, "B1", 10.0, 10.0));
        fp.add_block(Block::new(1, "B2", 10.0, 10.0));
        fp.blocks[0].x = Some(0.0);
        fp.blocks[0].y = Some(0.0);
        fp.blocks[1].x = Some(50.0);
        fp.blocks[1].y = Some(50.0);
        fp.add_net(vec![0, 1]);
        let hpwl = fp.hpwl();
        assert!(hpwl > 0.0);
    }

    #[test]
    fn test_simulated_annealing_creation() {
        let sa = SimulatedAnnealing::new();
        assert_eq!(sa.initial_temp, 10000.0);
    }
}