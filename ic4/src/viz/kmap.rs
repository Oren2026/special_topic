use crate::synthesis::{Kmap, Minterm};

pub fn draw_kmap(kmap: &Kmap) -> String {
    let n = kmap.n;
    let mut output = String::new();

    let gray = Kmap::gray_code(n);

    let label_row = if n == 2 {
        "        │ A=0       │ A=1       ".to_string()
    } else if n == 3 {
        "        │ AB=00     │ AB=01     │ AB=11     │ AB=10     ".to_string()
    } else {
        let half = n / 2;
        "        │ A=0       │ A=1       ".to_string()
    };

    output.push_str(&format!("┌────────{}┐\n", "─".repeat(label_row.len() - 8)));
    output.push_str(&format!("│ K-map   {}│\n", " ".repeat(label_row.len() - 10)));
    output.push_str(&format!("├────────{}┤\n", "─".repeat(label_row.len() - 8)));

    let b_label = if n >= 2 {
        " B\\A  ".to_string()
    } else {
        " \\A  ".to_string()
    };

    output.push_str(&format!("│{}│\n", b_label));
    output.push('\n');

    for (row_idx, bg) in gray.iter().enumerate() {
        let row_minterms: Vec<&Minterm> = kmap.minterms.iter()
            .filter(|m| !m.is_dc && m.vars.len() >= 2 && m.vars[1] == (row_idx % 2 == 1))
            .collect();
    }

    let col_count = 1 << (n / 2);
    let row_count = 1 << ((n + 1) / 2);

    for row in 0..row_count {
        let row_gray = &gray[row];
        let row_str = format!("  {}  │", if row_gray.contains('1') { "1" } else { "0" });

        for col in 0..col_count {
            let col_gray = &gray[col + col_count];
            let cell_val = if row_gray == "0" && col_gray == "0" {
                0
            } else if row_gray == "0" && col_gray == "1" {
                1
            } else if row_gray == "1" && col_gray == "1" {
                3
            } else {
                2
            };

            let is_minterm = kmap.minterms.iter().any(|m| m.value() == cell_val && !m.is_dc);
            let is_dc = kmap.minterms.iter().any(|m| m.value() == cell_val && m.is_dc);

            let cell_str = if is_minterm {
                format!(" \x1b[1;32m{}\x1b[0m ", cell_val)
            } else if is_dc {
                format!(" \x1b[33m{}\x1b[0m ", cell_val)
            } else {
                format!(" {} ", cell_val)
            };

            output.push_str(&format!("{}{}", row_str, cell_str));
        }
        output.push('\n');
    }

    let mut minterm_list = String::new();
    for m in &kmap.minterms {
        if !m.is_dc {
            minterm_list.push_str(&format!("{}, ", m.value()));
        }
    }
    if minterm_list.len() > 2 {
        minterm_list.truncate(minterm_list.len() - 2);
    }

    output.push_str(&format!("\n\x1b[36mMinterms:\x1b[0m {{{}}}\n", minterm_list));

    let dc_list: String = kmap.minterms.iter()
        .filter(|m| m.is_dc)
        .map(|m| format!("{}", m.value()))
        .collect::<Vec<_>>()
        .join(", ");

    if !dc_list.is_empty() {
        output.push_str(&format!("\x1b[33mDon't Care:\x1b[0m {{{}}}\n", dc_list));
    }

    output
}

pub fn draw_kmap_simple(kmap: &Kmap) -> String {
    let n = kmap.n;
    let mut output = String::new();

    let gray = Kmap::gray_code(n);

    let col_count = 1 << (n / 2);

    let header = if n == 2 {
        "  │ A=0  A=1  "
    } else if n == 3 {
        "  │ AB=00 AB=01 AB=11 AB=10"
    } else {
        "  │ A=0   A=1   "
    };

    output.push_str(&format!("┌───├{}┐\n", "─".repeat(header.len() - 4)));
    output.push_str(&format!("│   │{}│\n", header));
    output.push_str(&format!("├───├{}┤\n", "─".repeat(header.len() - 4)));

    let row_count = 1 << ((n + 1) / 2);

    for row in 0..row_count {
        let row_gray = &gray[row];
        let row_label = if row_gray.contains('1') { "1" } else { "0" };
        output.push_str(&format!("│ {} │", row_label));

        for col in 0..col_count {
            let col_gray = &gray[col + col_count];
            let mut val = 0;
            for (i, g) in row_gray.chars().enumerate() {
                if g == '1' {
                    val |= 1 << i;
                }
            }
            for (i, g) in col_gray.chars().enumerate() {
                if g == '1' {
                    val |= 1 << (i + n/2);
                }
            }

            let is_minterm = kmap.minterms.iter().any(|m| m.value() == val && !m.is_dc);
            let is_dc = kmap.minterms.iter().any(|m| m.value() == val && m.is_dc);

            let cell = if is_minterm {
                format!("\x1b[1;32m{:2}\x1b[0m", val)
            } else if is_dc {
                format!("\x1b[33m{:2}\x1b[0m", val)
            } else {
                format!("{:2}", val)
            };

            output.push_str(&format!(" {} │", cell));
        }
        output.push('\n');
    }

    output.push_str(&format!("\nLegend: \x1b[1;32mgreen\x1b[0m=minterm, \x1b[33myellow\x1b[0m=don't care\n"));

    output
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_draw_kmap_2var() {
        let kmap = Kmap::new(
            vec!["A".to_string(), "B".to_string()],
            vec![
                Minterm::new(vec![false, false]),
                Minterm::new(vec![false, true]),
            ],
        );
        let output = draw_kmap_simple(&kmap);
        assert!(!output.is_empty());
        assert!(output.contains("0"));
    }

    #[test]
    fn test_draw_kmap_3var() {
        let kmap = Kmap::new(
            vec!["A".to_string(), "B".to_string(), "C".to_string()],
            vec![
                Minterm::new(vec![false, false, false]),
                Minterm::new(vec![true, false, false]),
                Minterm::new(vec![true, true, false]),
            ],
        );
        let output = draw_kmap_simple(&kmap);
        assert!(!output.is_empty());
    }
}