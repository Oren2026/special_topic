use ic4::prelude::*;

// CPU 架構展示
// 1. 控制訊號生成（用 K-map 化簡）
// 2. CPU 區塊版面規劃（Floorplan）
// 3. 模組配置（Placement）
// 4. 訊號連線（Routing）

fn main() {
    println!("╔════════════════════════════════════════╗");
    println!("║   IC4 - CPU Architecture Demo           ║");
    println!("╚════════════════════════════════════════╝");
    println!();
    
    // 1. 控制訊號 (Control Signals)
    // 假設 3-bit opcode: 000=ADD, 001=SUB, 010=AND, 011=OR, 100=NOT
    // RegWrite = f(opcode) — 哪些 opcode 要寫入暫存器
    // 000(ADD)=1, 001(SUB)=1, 010(AND)=1, 011(OR)=1, 100(NOT)=0
    let regwrite_kmap = Kmap::new(
        vec!["opcode[2]".to_string(), "opcode[1]".to_string(), "opcode[0]".to_string()],
        vec![
            Minterm::new(vec![false, false, false]),  // 000 ADD - write
            Minterm::new(vec![false, false, true]),   // 001 SUB - write
            Minterm::new(vec![false, true, false]),   // 010 AND - write
            Minterm::new(vec![false, true, true]),    // 011 OR - write
            // 100 NOT 不寫入（implicit don't-care）
        ],
    );
    println!("=== 1. 控制訊號合成 ===");
    println!("Opcode: 000=ADD, 001=SUB, 010=AND, 011=OR, 100=NOT");
    println!("RegWrite K-map:");
    print!("{}", draw_kmap_simple(&regwrite_kmap));
    
    // ALU 控制訊號
    let alu_kmap = Kmap::new(
        vec!["opcode[1]".to_string(), "opcode[0]".to_string()],
        vec![
            Minterm::new(vec![false, false]),  // 00 → ADD
            Minterm::new(vec![false, true]),   // 01 → SUB
            Minterm::new(vec![true, false]),   // 10 → AND
            Minterm::new(vec![true, true]),    // 11 → OR/NOT (化簡後)
        ],
    );
    println!("ALUOp K-map:");
    print!("{}", draw_kmap_simple(&alu_kmap));
    
    // 2. CPU 版面規劃
    println!("\n=== 2. CPU Floorplan ===");
    let die = Rect::new(0.0, 0.0, 80.0, 60.0);
    let mut fp = Floorplan::new(die);
    
    fp.add_block(Block::new(0, "CTRL", 20.0, 15.0));  // 控制單元
    fp.add_block(Block::new(1, "ALU", 15.0, 20.0));   // 算術邏輯單元
    fp.add_block(Block::new(2, "REG", 25.0, 15.0));   // 暫存器檔
    fp.add_block(Block::new(3, "MEM", 20.0, 20.0));   // 記憶體
    
    // 手動配置位置（模擬實際佈局）
    fp.blocks[0].x = Some(5.0);   // CTRL 左上
    fp.blocks[0].y = Some(5.0);
    fp.blocks[1].x = Some(30.0);  // ALU 右上
    fp.blocks[1].y = Some(5.0);
    fp.blocks[2].x = Some(5.0);   // REG 左下
    fp.blocks[2].y = Some(25.0);
    fp.blocks[3].x = Some(35.0);  // MEM 右下
    fp.blocks[3].y = Some(25.0);
    
    fp.add_net(vec![0, 1]);  // CTRL → ALU 控制訊號線
    fp.add_net(vec![0, 2]);  // CTRL → REG
    fp.add_net(vec![1, 2]);  // ALU ↔ REG 資料線
    fp.add_net(vec![2, 3]);  // REG ↔ MEM
    fp.add_net(vec![0, 3]);  // CTRL → MEM
    
    println!("CPU 區塊:");
    for b in &fp.blocks {
        if let Some(r) = b.rect() {
            println!("  {}: {:.0}x{:.0} at ({:.0},{:.0})", b.name, b.width, b.height, r.x1, r.y1);
        }
    }
    println!("HPWL: {:.1}", fp.hpwl());
    print!("{}", draw_floorplan_simple(&fp));
    
    // 3. 模組配置
    println!("\n=== 3. Module Placement ===");
    let blocks = vec![
        PlaceBlock::new(0, 12.0, 8.0),  // CTRL
        PlaceBlock::new(1, 10.0, 10.0), // ALU
        PlaceBlock::new(2, 15.0, 8.0),  // REG
        PlaceBlock::new(3, 12.0, 12.0), // MEM
    ];
    
    let mut placer = GridPlacer::new(2, 5.0);
    let mut placed = blocks.clone();
    placer.place(&mut placed);
    
    println!("配置後:");
    for b in &placed {
        println!("  Block {}: ({:.1}, {:.1})", b.id, b.x.unwrap_or(0.0), b.y.unwrap_or(0.0));
    }
    print!("{}", draw_placement_simple(&placed, 2));
    
    // 4. 訊號連線
    println!("\n=== 4. Signal Routing ===");
    let mut grid = Grid::new(16, 8);
    
    // 設定針腳（CPU 訊號埠）
    grid.set_pin(0, 3);   // CTRL out
    grid.set_pin(15, 3); // ALU in/out
    grid.set_pin(0, 6);  // REG in
    grid.set_pin(15, 6); // MEM in/out
    
    // 額外障礙物（其他訊號線佔用的格子）
    grid.set_obstacle(8, 2);
    grid.set_obstacle(8, 4);
    grid.set_obstacle(4, 5);
    grid.set_obstacle(12, 5);
    
    let mut router = LeeRouter::new();
    let route1 = router.route(&grid, Coordinate::new(0, 3), Coordinate::new(15, 3));
    let route2 = router.route(&grid, Coordinate::new(0, 6), Coordinate::new(15, 6));
    
    println!("網格: 16x8, 針腳: (0,3), (15,3), (0,6), (15,6)");
    if let Some(path) = &route1 {
        println!("資料匯流排: {} 段", path.len());
    }
    if let Some(path) = &route2 {
        println!("控制匯流排: {} 段", path.len());
    }
    print!("{}", draw_grid(&grid));
    
    if let Some(path) = route1 {
        print!("{}", draw_route_path(&grid, Coordinate::new(0, 3), Coordinate::new(15, 3)));
    }
    if let Some(path) = route2 {
        print!("{}", draw_route_path(&grid, Coordinate::new(0, 6), Coordinate::new(15, 6)));
    }
    
    println!("\n╔════════════════════════════════════════╗");
    println!("║   Demo Complete                        ║");
    println!("╚════════════════════════════════════════╝");
}