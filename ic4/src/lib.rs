pub mod synthesis;
pub mod physical;
pub mod viz;

pub use synthesis::{Signal, Kmap, Minterm, QuineMcCluskey, TechMapper, Library, Cell};
pub use physical::{Point, Rect, Floorplan, Block, Placer, GridPlacer, ForceDirectPlacer, PlaceBlock};
pub use physical::{Grid, GridValue, Coordinate, Router, LeeRouter, MazeRouter, ChannelRouter};

pub mod prelude {
    pub use crate::synthesis::{Kmap, Minterm, QuineMcCluskey, TechMapper, Library, Cell, Signal};
    pub use crate::physical::{Point, Rect, Floorplan, Block, Placer, GridPlacer, ForceDirectPlacer, PlaceBlock};
    pub use crate::physical::{Grid, GridValue, Coordinate, Router, LeeRouter, MazeRouter, ChannelRouter};
    pub use crate::viz::kmap::{draw_kmap, draw_kmap_simple};
    pub use crate::viz::floorplan::{draw_floorplan, draw_floorplan_simple};
    pub use crate::viz::placement::{draw_placement, draw_placement_simple};
    pub use crate::viz::routing::{draw_grid, draw_grid_with_routes, draw_route_path};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_signal_var() {
        let s = Signal::var("a");
        assert_eq!(format!("{:?}", s), "Var(\"a\")");
    }

    #[test]
    fn test_signal_and_or() {
        let a = Signal::var("a");
        let b = Signal::var("b");
        let ab = a.and(b);
        let c = Signal::var("c");
        let abc = ab.or(c);
        match abc {
            Signal::Or(_) => {},
            _ => panic!("Expected Or"),
        }
    }

    #[test]
    fn test_kmap() {
        let kmap = Kmap::new(
            vec!["A".to_string(), "B".to_string()],
            vec![Minterm::new(vec![false, false])],
        );
        assert_eq!(kmap.n, 2);
    }

    #[test]
    fn test_quine_mccluskey() {
        let mut qm = QuineMcCluskey::new(3);
        qm.add_minterm(0);
        qm.add_minterm(1);
        qm.add_minterm(2);
        qm.add_minterm(3);
        let implicants = qm.minimize();
        assert!(!implicants.is_empty());
    }

    #[test]
    fn test_tech_mapper() {
        let lib = Library::standard_cells();
        let mapper = TechMapper::new(lib);
        let mut netlist = crate::synthesis::techmap::Netlist::new();
        netlist.add_node("A & B".to_string(), vec!["a".to_string(), "b".to_string()], "y".to_string());
        let result = mapper.map(&netlist);
        assert!(result.total_area > 0.0);
    }

    #[test]
    fn test_point_distance() {
        let p1 = Point::new(0.0, 0.0);
        let p2 = Point::new(3.0, 4.0);
        assert_eq!(p1.distance(&p2), 5.0);
    }

    #[test]
    fn test_rect_area() {
        let r = Rect::new(0.0, 0.0, 10.0, 5.0);
        assert_eq!(r.area(), 50.0);
    }

    #[test]
    fn test_rect_center() {
        let r = Rect::new(0.0, 0.0, 10.0, 6.0);
        let c = r.center();
        assert_eq!(c.x, 5.0);
        assert_eq!(c.y, 3.0);
    }

    #[test]
    fn test_floorplan() {
        let die = Rect::new(0.0, 0.0, 100.0, 100.0);
        let mut fp = Floorplan::new(die);
        fp.add_block(Block::new(0, "B1", 10.0, 10.0));
        fp.add_block(Block::new(1, "B2", 20.0, 10.0));
        fp.pack_slicing();

        assert!(fp.blocks[0].x.is_some());
        assert!(fp.blocks[1].x.is_some());
    }

    #[test]
    fn test_grid_placer() {
        let mut placer = GridPlacer::new(2, 10.0);
        let mut blocks = vec![
            PlaceBlock::new(0, 10.0, 5.0),
            PlaceBlock::new(1, 15.0, 5.0),
            PlaceBlock::new(2, 20.0, 5.0),
        ];
        placer.place(&mut blocks);

        assert!(blocks[0].x.is_some());
        assert!(blocks[1].x.is_some());
    }

    #[test]
    fn test_lee_router() {
        let mut grid = Grid::new(10, 10);
        grid.set_pin(0, 0);
        grid.set_pin(9, 9);

        let mut router = LeeRouter::new();
        let route = router.route(&grid, Coordinate::new(0, 0), Coordinate::new(9, 9));

        assert!(route.is_some());
    }

    #[test]
    fn test_channel_router() {
        let router = ChannelRouter::new();
        let tracks = router.route_channel(&[1, 2, 3], &[3, 2, 1], 3);
        assert!(!tracks.is_empty());
    }
}