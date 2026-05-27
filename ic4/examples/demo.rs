use ic4::prelude::*;

fn demo_kmap() {
    println!("=== Karnaugh Map 邏輯優化 ===");
    let kmap = Kmap::new(
        vec!["A".to_string(), "B".to_string(), "C".to_string()],
        vec![
            Minterm::new(vec![false, false, false]),
            Minterm::new(vec![false, false, true]),
            Minterm::new(vec![false, true, false]),
            Minterm::new(vec![true, false, false]),
            Minterm::new(vec![true, false, true]),
            Minterm::new(vec![true, true, false]),
        ],
    );
    let primes = kmap.simplify();
    println!("質蘊含項 (Prime Implicants): {:?}", primes.len());
    for p in &primes {
        println!("  {:?}", p.vars);
    }
    println!();
    print!("{}", draw_kmap_simple(&kmap));
}

fn demo_quine_mccluskey() {
    println!("=== Quine-McCluskey 演算法 ===");
    let mut qm = QuineMcCluskey::new(4);
    qm.add_minterm(0);
    qm.add_minterm(1);
    qm.add_minterm(2);
    qm.add_minterm(4);
    qm.add_minterm(5);
    qm.add_minterm(6);
    qm.add_minterm(8);
    qm.add_minterm(9);
    qm.add_minterm(10);
    qm.add_minterm(12);
    qm.add_minterm(14);

    println!("最小項: {:?}", qm.minterms);
    let implicants = qm.minimize();
    println!("化簡後的蘊含項:");
    for imp in &implicants {
        println!("  {}", imp);
    }
    println!();
}

fn demo_tech_mapping() {
    println!("=== 技術映射 (Technology Mapping) ===");
    let lib = Library::standard_cells();
    println!("標準單元庫包含 {} 個單元:", lib.cells.len());
    for (name, cell) in &lib.cells {
        println!("  {}: area={}, delay={}", name, cell.area, cell.delay);
    }

    let mapper = TechMapper::new(lib);

    let mut netlist = ic4::synthesis::techmap::Netlist::new();
    netlist.add_node(
        "A & B".to_string(),
        vec!["a".to_string(), "b".to_string()],
        "y".to_string(),
    );
    netlist.add_node(
        "Y | C".to_string(),
        vec!["y".to_string(), "c".to_string()],
        "z".to_string(),
    );

    let result = mapper.map(&netlist);
    println!("\n映射結果:");
    println!("  總面積: {}", result.total_area);
    println!("  總延遲: {}", result.total_delay);
    println!("  執行個體:");
    for inst in &result.instances {
        println!("    {} -> {}", inst.cell_name, inst.output);
    }
    println!();
}

fn demo_floorplanning() {
    println!("===  Floorplanning ( 版面規劃 ) ===");
    let die = Rect::new(0.0, 0.0, 100.0, 100.0);
    let mut fp = Floorplan::new(die);

    fp.add_block(Block::new(0, "CPU", 30.0, 20.0));
    fp.add_block(Block::new(1, "ALU", 15.0, 15.0));
    fp.add_block(Block::new(2, "REG", 20.0, 10.0));
    fp.add_block(Block::new(3, "CACHE", 25.0, 15.0));

    println!("初始區塊:");
    for b in &fp.blocks {
        println!("  {}: {}x{}", b.name, b.width, b.height);
    }

    fp.pack_slicing();
    println!("\n切片式包裝後:");
    for b in &fp.blocks {
        if let Some(rect) = b.rect() {
            println!("  {}: ({:.1}, {:.1}) - ({:.1}, {:.1})",
                b.name, rect.x1, rect.y1, rect.x2, rect.y2);
        }
    }

    fp.blocks[0].x = Some(0.0);
    fp.blocks[0].y = Some(0.0);
    fp.blocks[1].x = Some(35.0);
    fp.blocks[1].y = Some(0.0);
    fp.blocks[2].x = Some(0.0);
    fp.blocks[2].y = Some(25.0);
    fp.blocks[3].x = Some(35.0);
    fp.blocks[3].y = Some(25.0);

    fp.add_net(vec![0, 1]);
    fp.add_net(vec![1, 2]);
    fp.add_net(vec![2, 3]);
    fp.add_net(vec![0, 3]);

    let hpwl = fp.hpwl();
    let cost = fp.calc_cost(0.5);
    println!("\nHPWL: {:.2}", hpwl);
    println!("成本 (alpha=0.5): {:.2}", cost);
    println!();

    print!("{}", draw_floorplan_simple(&fp));
}

fn demo_placement() {
    println!("=== Placement ( 配置 ) ===");
    let mut blocks = vec![
        PlaceBlock::new(0, 10.0, 5.0),
        PlaceBlock::new(1, 8.0, 6.0),
        PlaceBlock::new(2, 12.0, 4.0),
        PlaceBlock::new(3, 6.0, 7.0),
    ];

    println!("初始位置:");
    for b in &blocks {
        println!("  Block {}: {:?}", b.id, (b.x, b.y));
    }

    let mut placer = GridPlacer::new(2, 10.0);
    placer.place(&mut blocks);

    println!("\n網格配置後:");
    for b in &blocks {
        println!("  Block {}: ({:.1}, {:.1})", b.id, b.x.unwrap_or(0.0), b.y.unwrap_or(0.0));
    }
    println!();

    print!("{}", draw_placement_simple(&blocks, 2));
}

fn demo_routing() {
    println!("=== Routing ( 布線 ) ===");
    let mut grid = Grid::new(20, 10);

    grid.set_pin(0, 4);
    grid.set_pin(19, 4);
    grid.set_pin(0, 9);
    grid.set_pin(19, 9);

    println!("網格大小: {}x{}", grid.width, grid.height);
    println!("針腳: (0,4), (19,4), (0,9), (19,9)");

    let mut router = LeeRouter::new();
    let route1 = router.route(&grid, Coordinate::new(0, 4), Coordinate::new(19, 4));
    let route2 = router.route(&grid, Coordinate::new(0, 9), Coordinate::new(19, 9));

    println!("\nLee's 演算法路由:");
    if let Some(path) = route1 {
        println!("  路由1: {} 段", path.len());
    }
    if let Some(path) = route2 {
        println!("  路由2: {} 段", path.len());
    }

    let maze = MazeRouter::new();
    let routes = maze.find_all_routes(
        &grid,
        &[
            (Coordinate::new(0, 4), Coordinate::new(19, 4)),
            (Coordinate::new(0, 9), Coordinate::new(19, 9)),
        ],
    );
    println!("\n迷宮路由器找到 {} 條路由", routes.len());
    println!();

    print!("{}", draw_grid(&grid));
    print!("{}", draw_route_path(&grid, Coordinate::new(0, 4), Coordinate::new(19, 4)));
}

fn demo_signal_optimization() {
    println!("=== 信號優化 ===");
    let a = Signal::var("a");
    let b = Signal::var("b");
    let c = Signal::var("c");

    let expr1 = a.and(b.clone());
    let expr2 = expr1.or(c.clone());
    let expr3 = expr2.not();

    println!("原始表達式: !((a & b) | c)");
    println!("信號類型: {:?}", expr3);

    let mut qm = QuineMcCluskey::new(3);
    qm.add_minterm(0);
    qm.add_minterm(1);
    qm.add_minterm(2);
    let implicants = qm.minimize();
    println!("化簡後: {:?}", implicants);
    println!();
}

fn main() {
    println!("╔════════════════════════════════════════╗");
    println!("║     IC4 - IC 設計演示套件               ║");
    println!("║     IC Design Demonstration Package    ║");
    println!("╚════════════════════════════════════════╝");
    println!();

    demo_signal_optimization();
    demo_kmap();
    demo_quine_mccluskey();
    demo_tech_mapping();
    demo_floorplanning();
    demo_placement();
    demo_routing();

    println!("╔════════════════════════════════════════╗");
    println!("║     演示完成                           ║");
    println!("╚════════════════════════════════════════╝");
}