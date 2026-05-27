use eframe::egui;
use ic4::prelude::*;

struct IC4DemoApp;

impl eframe::App for IC4DemoApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("IC4 - IC Design Visualization");
            ui.separator();

            let width = ui.available_width() / 2.0 - 10.0;
            let height = 300.0;

            ui.columns(2, |cols| {
                cols[0].heading("1. K-map");
                let (response, painter) = cols[0].allocate_painter(
                    egui::vec2(width, height),
                    egui::Sense::hover(),
                );
                self.draw_kmap(&response, &painter);

                cols[1].heading("2. Floorplan");
                let (response, painter) = cols[1].allocate_painter(
                    egui::vec2(width, height),
                    egui::Sense::hover(),
                );
                self.draw_floorplan(&response, &painter);
            });

            ui.columns(2, |cols| {
                cols[0].heading("3. Placement");
                let (response, painter) = cols[0].allocate_painter(
                    egui::vec2(width, height),
                    egui::Sense::hover(),
                );
                self.draw_placement(&response, &painter);

                cols[1].heading("4. Routing");
                let (response, painter) = cols[1].allocate_painter(
                    egui::vec2(width, height),
                    egui::Sense::hover(),
                );
                self.draw_routing(&response, &painter);
            });

            ui.separator();
            ui.label("使用說明：上方 K-map 綠色為最小項，Floorplan 彩色方塊為區塊，Placement 顯示配置，Routing 黃色=針腳/青色粉色=路由線");
        });
    }
}

impl IC4DemoApp {
    fn draw_kmap(&self, response: &egui::Response, painter: &egui::Painter) {
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

        let rect = response.rect;
        let cell_width = rect.width() / 4.0;
        let cell_height = rect.height() / 4.0;

        let gray = Kmap::gray_code(3);
        let col_count = 4;

        painter.rect_filled(rect, 0.0, egui::Color32::from_gray(30));

        for row in 0..4 {
            for col in 0..4 {
                let cell_rect = egui::Rect::from_min_size(
                    egui::pos2(rect.min.x + col as f32 * cell_width, rect.min.y + row as f32 * cell_height),
                    egui::vec2(cell_width, cell_height),
                );

                let row_gray = &gray[row];
                let col_gray = &gray[col + col_count];
                let mut val = 0;
                for (i, g) in row_gray.chars().enumerate() {
                    if g == '1' { val |= 1 << i; }
                }
                for (i, g) in col_gray.chars().enumerate() {
                    if g == '1' { val |= 1 << (i + 1); }
                }

                let is_minterm = kmap.minterms.iter().any(|m| m.value() == val && !m.is_dc);

                let color = if is_minterm {
                    egui::Color32::from_rgb(0, 200, 100)
                } else {
                    egui::Color32::from_gray(60)
                };

                painter.rect_filled(cell_rect, 2.0, color);
                painter.text(
                    cell_rect.center(),
                    egui::Align2::CENTER_CENTER,
                    format!("{}", val),
                    egui::FontId::proportional(cell_width.min(cell_height) * 0.25),
                    egui::Color32::WHITE,
                );
            }
        }
    }

    fn draw_floorplan(&self, response: &egui::Response, painter: &egui::Painter) {
        let die = Rect::new(0.0, 0.0, 100.0, 100.0);
        let mut fp = Floorplan::new(die);

        fp.add_block(Block::new(0, "CPU", 30.0, 20.0));
        fp.add_block(Block::new(1, "ALU", 15.0, 15.0));
        fp.add_block(Block::new(2, "REG", 20.0, 10.0));
        fp.add_block(Block::new(3, "CACHE", 25.0, 15.0));

        fp.blocks[0].x = Some(5.0);
        fp.blocks[0].y = Some(5.0);
        fp.blocks[1].x = Some(40.0);
        fp.blocks[1].y = Some(5.0);
        fp.blocks[2].x = Some(5.0);
        fp.blocks[2].y = Some(30.0);
        fp.blocks[3].x = Some(40.0);
        fp.blocks[3].y = Some(30.0);

        let rect = response.rect;
        let scale_x = rect.width() / 110.0;
        let scale_y = rect.height() / 110.0;
        let scale = scale_x.min(scale_y);

        painter.rect_filled(rect, 0.0, egui::Color32::from_gray(20));

        let colors = [
            egui::Color32::from_rgb(200, 100, 100),
            egui::Color32::from_rgb(100, 200, 100),
            egui::Color32::from_rgb(100, 100, 200),
            egui::Color32::from_rgb(200, 200, 100),
        ];

        for (i, block) in fp.blocks.iter().enumerate() {
            if let Some(r) = block.rect() {
                let x = r.x1 as f32 * scale;
                let y = r.y1 as f32 * scale;
                let w = r.width() as f32 * scale;
                let h = r.height() as f32 * scale;

                let block_rect = egui::Rect::from_min_size(
                    egui::pos2(rect.min.x + x, rect.min.y + y),
                    egui::vec2(w, h),
                );

                painter.rect_filled(block_rect, 4.0, colors[i]);
                painter.text(
                    block_rect.left_top() + egui::vec2(4.0, 4.0),
                    egui::Align2::LEFT_TOP,
                    &block.name,
                    egui::FontId::proportional(14.0),
                    egui::Color32::WHITE,
                );
            }
        }
    }

    fn draw_placement(&self, response: &egui::Response, painter: &egui::Painter) {
        let blocks = vec![
            PlaceBlock::new(0, 20.0, 15.0),
            PlaceBlock::new(1, 15.0, 12.0),
            PlaceBlock::new(2, 18.0, 10.0),
            PlaceBlock::new(3, 12.0, 8.0),
        ];

        let mut placer = GridPlacer::new(2, 10.0);
        let mut placed = blocks.clone();
        placer.place(&mut placed);

        let rect = response.rect;
        let max_x = placed.iter().filter_map(|b| b.x.map(|x| x + b.width)).fold(100.0, f64::max);
        let max_y = placed.iter().filter_map(|b| b.y.map(|y| y + b.height)).fold(100.0, f64::max);

        let scale_x = rect.width() / (max_x as f32 + 20.0);
        let scale_y = rect.height() / (max_y as f32 + 20.0);
        let scale = scale_x.min(scale_y);

        painter.rect_filled(rect, 0.0, egui::Color32::from_gray(25));

        let colors = [
            egui::Color32::from_rgb(255, 180, 100),
            egui::Color32::from_rgb(100, 255, 180),
            egui::Color32::from_rgb(180, 100, 255),
            egui::Color32::from_rgb(255, 100, 180),
        ];

        for (i, block) in placed.iter().enumerate() {
            if let (Some(x), Some(y)) = (block.x, block.y) {
                let px = x as f32 * scale;
                let py = y as f32 * scale;
                let w = block.width as f32 * scale;
                let h = block.height as f32 * scale;

                let block_rect = egui::Rect::from_min_size(
                    egui::pos2(rect.min.x + px, rect.min.y + py),
                    egui::vec2(w, h),
                );

                painter.rect_filled(block_rect, 2.0, colors[i]);
                painter.text(
                    block_rect.center(),
                    egui::Align2::CENTER_CENTER,
                    format!("{}", block.id),
                    egui::FontId::proportional(16.0),
                    egui::Color32::WHITE,
                );
            }
        }
    }

    fn draw_routing(&self, response: &egui::Response, painter: &egui::Painter) {
        let mut grid = Grid::new(20, 10);
        grid.set_pin(0, 2);
        grid.set_pin(19, 2);
        grid.set_pin(0, 7);
        grid.set_pin(19, 7);

        let mut router = LeeRouter::new();
        let route1 = router.route(&grid, Coordinate::new(0, 2), Coordinate::new(19, 2));
        let route2 = router.route(&grid, Coordinate::new(0, 7), Coordinate::new(19, 7));

        let rect = response.rect;
        let cell_w = rect.width() / 20.0;
        let cell_h = rect.height() / 10.0;

        for y in 0..10 {
            for x in 0..20 {
                let cell_rect = egui::Rect::from_min_size(
                    egui::pos2(rect.min.x + x as f32 * cell_w, rect.min.y + y as f32 * cell_h),
                    egui::vec2(cell_w, cell_h),
                );

                let cell = grid.get(x, y);
                let color = match cell {
                    Some(GridValue::Pin) => egui::Color32::from_rgb(255, 255, 0),
                    Some(GridValue::Obstacle) => egui::Color32::from_gray(80),
                    _ => egui::Color32::from_gray(40),
                };

                painter.rect_filled(cell_rect, 1.0, color);
            }
        }

        let route_color1 = egui::Color32::from_rgb(0, 200, 255);
        let route_color2 = egui::Color32::from_rgb(255, 100, 200);

        if let Some(path) = route1 {
            for &coord in &path {
                let cx = coord.x as f32;
                let cy = coord.y as f32;
                let cell_rect = egui::Rect::from_min_size(
                    egui::pos2(rect.min.x + cx * cell_w, rect.min.y + cy * cell_h),
                    egui::vec2(cell_w, cell_h),
                );
                painter.rect_filled(cell_rect, 1.0, route_color1);
            }
        }

        if let Some(path) = route2 {
            for &coord in &path {
                let cx = coord.x as f32;
                let cy = coord.y as f32;
                let cell_rect = egui::Rect::from_min_size(
                    egui::pos2(rect.min.x + cx * cell_w, rect.min.y + cy * cell_h),
                    egui::vec2(cell_w, cell_h),
                );
                painter.rect_filled(cell_rect, 1.0, route_color2);
            }
        }
    }
}

fn main() {
    let options = eframe::NativeOptions::default();
    eframe::run_native(
        "IC4 - IC Design Visualization",
        options,
        Box::new(|_cc| Ok(Box::new(IC4DemoApp))),
    ).unwrap();
}