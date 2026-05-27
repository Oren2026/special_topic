pub mod floorplan;
pub mod place;
pub mod route;

pub use floorplan::{Floorplan, Block, SimulatedAnnealing, Wirelength};
pub use place::{Placer, GridPlacer, ForceDirectPlacer, PlaceBlock};
pub use route::{Router, LeeRouter, MazeRouter, Grid, GridValue, Coordinate, ChannelRouter};

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

impl Point {
    pub fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    pub fn distance(&self, other: &Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rect {
    pub x1: f64,
    pub y1: f64,
    pub x2: f64,
    pub y2: f64,
}

impl Rect {
    pub fn new(x1: f64, y1: f64, x2: f64, y2: f64) -> Self {
        Rect { x1, y1, x2, y2 }
    }

    pub fn width(&self) -> f64 {
        self.x2 - self.x1
    }

    pub fn height(&self) -> f64 {
        self.y2 - self.y1
    }

    pub fn area(&self) -> f64 {
        self.width() * self.height()
    }

    pub fn center(&self) -> Point {
        Point::new((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)
    }

    pub fn overlaps(&self, other: &Rect) -> bool {
        self.x1 < other.x2 && self.x2 > other.x1 &&
        self.y1 < other.y2 && self.y2 > other.y1
    }
}