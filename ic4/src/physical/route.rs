use std::collections::{HashMap, VecDeque};

#[derive(Debug, Clone, PartialEq)]
pub enum GridValue {
    Empty,
    Obstacle,
    Wire,
    Pin,
}

pub struct Grid {
    pub width: usize,
    pub height: usize,
    pub cells: Vec<Vec<GridValue>>,
}

impl Grid {
    pub fn new(width: usize, height: usize) -> Self {
        let cells = vec![vec![GridValue::Empty; width]; height];
        Grid { width, height, cells }
    }

    pub fn set_obstacle(&mut self, x: usize, y: usize) {
        if x < self.width && y < self.height {
            self.cells[y][x] = GridValue::Obstacle;
        }
    }

    pub fn set_pin(&mut self, x: usize, y: usize) {
        if x < self.width && y < self.height {
            self.cells[y][x] = GridValue::Pin;
        }
    }

    pub fn get(&self, x: usize, y: usize) -> Option<GridValue> {
        if x < self.width && y < self.height {
            Some(self.cells[y][x].clone())
        } else {
            None
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Coordinate {
    pub x: i32,
    pub y: i32,
}

impl Coordinate {
    pub fn new(x: i32, y: i32) -> Self {
        Coordinate { x, y }
    }
}

pub trait Router {
    fn route(&mut self, grid: &Grid, start: Coordinate, end: Coordinate) -> Option<Vec<Coordinate>>;
}

pub struct LeeRouter {
    pub max_iterations: usize,
}

impl LeeRouter {
    pub fn new() -> Self {
        LeeRouter { max_iterations: 10000 }
    }

    fn is_valid(&self, c: Coordinate, grid: &Grid) -> bool {
        c.x >= 0 && c.y >= 0 &&
        (c.x as usize) < grid.width &&
        (c.y as usize) < grid.height
    }

    fn is_passable(&self, c: Coordinate, grid: &Grid) -> bool {
        match grid.get(c.x as usize, c.y as usize) {
            Some(GridValue::Empty) | Some(GridValue::Pin) => true,
            _ => false,
        }
    }

    fn neighbors(&self, c: Coordinate) -> Vec<Coordinate> {
        vec![
            Coordinate::new(c.x + 1, c.y),
            Coordinate::new(c.x - 1, c.y),
            Coordinate::new(c.x, c.y + 1),
            Coordinate::new(c.x, c.y - 1),
        ]
    }
}

impl Default for LeeRouter {
    fn default() -> Self {
        Self::new()
    }
}

impl Router for LeeRouter {
    fn route(&mut self, grid: &Grid, start: Coordinate, end: Coordinate) -> Option<Vec<Coordinate>> {
        let mut visited: HashMap<Coordinate, Coordinate> = HashMap::new();
        let mut queue: VecDeque<Coordinate> = VecDeque::new();

        queue.push_back(start);
        visited.insert(start, start);

        while let Some(current) = queue.pop_front() {
            if current == end {
                let mut path = Vec::new();
                let mut c = end;
                while c != start {
                    path.push(c);
                    c = visited[&c];
                }
                path.push(start);
                path.reverse();
                return Some(path);
            }

            for neighbor in self.neighbors(current) {
                if self.is_valid(neighbor, grid) &&
                   self.is_passable(neighbor, grid) &&
                   !visited.contains_key(&neighbor) {
                    visited.insert(neighbor, current);
                    queue.push_back(neighbor);
                }
            }
        }

        None
    }
}

pub struct MazeRouter;

impl MazeRouter {
    pub fn new() -> Self {
        MazeRouter
    }

    pub fn find_all_routes(&self, grid: &Grid, nets: &[(Coordinate, Coordinate)]) -> Vec<Vec<Coordinate>> {
        let mut router = LeeRouter::new();
        let mut routes = Vec::new();

        for &(start, end) in nets {
            if let Some(route) = router.route(grid, start, end) {
                routes.push(route);
            }
        }

        routes
    }

    pub fn rip_up_reroute(&self, grid: &mut Grid, nets: &[(Coordinate, Coordinate)]) -> Vec<Vec<Coordinate>> {
        let mut routes = Vec::new();
        let mut router = LeeRouter::new();

        for &(start, end) in nets {
            for coord in routes.iter().flat_map(|r: &Vec<Coordinate>| r.iter()) {
                if let Some(GridValue::Wire) = grid.get(coord.x as usize, coord.y as usize) {
                    grid.cells[coord.y as usize][coord.x as usize] = GridValue::Empty;
                }
            }

            if let Some(route) = router.route(grid, start, end) {
                for &coord in &route {
                    if let Some(v) = grid.get(coord.x as usize, coord.y as usize) {
                        if v == GridValue::Empty {
                            grid.cells[coord.y as usize][coord.x as usize] = GridValue::Wire;
                        }
                    }
                }
                routes.push(route);
            }
        }

        routes
    }
}

impl Default for MazeRouter {
    fn default() -> Self {
        Self::new()
    }
}

pub struct ChannelRouter {
    pub track_height: f64,
}

impl ChannelRouter {
    pub fn new() -> Self {
        ChannelRouter { track_height: 1.0 }
    }

    pub fn route_channel(&self, pins_top: &[usize], pins_bottom: &[usize], height: usize) -> Vec<Vec<Option<usize>>> {
        let num_tracks = height;
        let width = pins_top.len().max(pins_bottom.len());

        let mut tracks: Vec<Vec<Option<usize>>> = vec![vec![None; width]; num_tracks];

        for (col, &top_pin) in pins_top.iter().enumerate() {
            let mut assigned = false;
            for track in 0..num_tracks {
                if tracks[track][col].is_none() {
                    tracks[track][col] = Some(top_pin);
                    assigned = true;
                    break;
                }
            }
            if !assigned && col < num_tracks {
                tracks[col][col] = Some(top_pin);
            }
        }

        for (col, &bottom_pin) in pins_bottom.iter().enumerate() {
            let mut assigned = false;
            for track in 0..num_tracks {
                if tracks[track][col].is_none() {
                    tracks[track][col] = Some(bottom_pin);
                    assigned = true;
                    break;
                }
            }
            if !assigned && col < num_tracks {
                if let Some(row) = tracks.iter_mut().find(|r| r[col].is_none()) {
                    row[col] = Some(bottom_pin);
                }
            }
        }

        tracks
    }
}

impl Default for ChannelRouter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_grid_creation() {
        let grid = Grid::new(10, 10);
        assert_eq!(grid.width, 10);
        assert_eq!(grid.height, 10);
    }

    #[test]
    fn test_grid_set_obstacle() {
        let mut grid = Grid::new(10, 10);
        grid.set_obstacle(5, 5);
        assert_eq!(grid.get(5, 5), Some(GridValue::Obstacle));
    }

    #[test]
    fn test_grid_set_pin() {
        let mut grid = Grid::new(10, 10);
        grid.set_pin(3, 3);
        assert_eq!(grid.get(3, 3), Some(GridValue::Pin));
    }

    #[test]
    fn test_lee_router() {
        let mut grid = Grid::new(10, 10);
        grid.set_pin(0, 0);
        grid.set_pin(9, 9);

        let mut router = LeeRouter::new();
        let route = router.route(&grid, Coordinate::new(0, 0), Coordinate::new(9, 9));

        assert!(route.is_some());
        let path = route.unwrap();
        assert!(!path.is_empty());
        assert_eq!(path.first(), Some(&Coordinate::new(0, 0)));
        assert_eq!(path.last(), Some(&Coordinate::new(9, 9)));
    }

    #[test]
    fn test_lee_router_blocked() {
        let mut grid = Grid::new(5, 5);
        grid.set_pin(0, 0);
        grid.set_pin(4, 4);
        grid.set_obstacle(2, 2);
        grid.set_obstacle(2, 3);

        let mut router = LeeRouter::new();
        let route = router.route(&grid, Coordinate::new(0, 0), Coordinate::new(4, 4));

        assert!(route.is_some());
    }

    #[test]
    fn test_maze_router() {
        let mut grid = Grid::new(10, 10);
        grid.set_pin(0, 0);
        grid.set_pin(9, 0);
        grid.set_pin(0, 9);
        grid.set_pin(9, 9);

        let maze = MazeRouter::new();
        let routes = maze.find_all_routes(&grid, &[
            (Coordinate::new(0, 0), Coordinate::new(9, 0)),
            (Coordinate::new(0, 9), Coordinate::new(9, 9)),
        ]);

        assert_eq!(routes.len(), 2);
    }

    #[test]
    fn test_channel_router() {
        let router = ChannelRouter::new();
        let tracks = router.route_channel(&[1, 2, 3], &[3, 2, 1], 3);

        assert_eq!(tracks.len(), 3);
    }

    #[test]
    fn test_coordinate() {
        let c = Coordinate::new(3, 4);
        assert_eq!(c.x, 3);
        assert_eq!(c.y, 4);
    }
}