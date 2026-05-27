use std::collections::{HashSet, BTreeMap, BTreeSet};

pub struct QuineMcCluskey {
    pub num_vars: usize,
    pub minterms: Vec<usize>,
    pub dont_cares: Vec<usize>,
}

impl QuineMcCluskey {
    pub fn new(num_vars: usize) -> Self {
        QuineMcCluskey {
            num_vars,
            minterms: Vec::new(),
            dont_cares: Vec::new(),
        }
    }

    pub fn add_minterm(&mut self, m: usize) {
        self.minterms.push(m);
    }

    pub fn add_dont_care(&mut self, d: usize) {
        self.dont_cares.push(d);
    }

    pub fn all_terms(&self) -> Vec<usize> {
        let mut all: Vec<usize> = self.minterms.clone();
        all.extend(self.dont_cares.clone());
        all.sort();
        all.dedup();
        all
    }

    fn to_binary_string(term: usize, bits: usize) -> String {
        format!("{:0width$b}", term, width = bits)
    }

    fn count_ones(s: &str) -> usize {
        s.chars().filter(|&c| c == '1').count()
    }

    fn can_combine(a: &str, b: &str) -> bool {
        let diffs: Vec<usize> = a.chars()
            .zip(b.chars())
            .enumerate()
            .filter(|(_, (x, y))| x != y)
            .map(|(i, _)| i)
            .collect();
        diffs.len() == 1
    }

    fn combine(a: &str, b: &str) -> String {
        a.chars()
            .zip(b.chars())
            .map(|(x, y)| if x == y { x } else { '-' })
            .collect()
    }

    pub fn minimize(&self) -> Vec<String> {
        let all = self.all_terms();
        if all.is_empty() {
            return vec!["0".to_string()];
        }

        if all.len() == 1 << self.num_vars {
            return vec![];
        }

        let mut groups: BTreeMap<usize, BTreeSet<String>> = BTreeMap::new();
        for &term in &all {
            let bin = Self::to_binary_string(term, self.num_vars);
            let ones = Self::count_ones(&bin);
            groups.entry(ones).or_default().insert(bin);
        }

        let mut prime_implicants: BTreeSet<String> = BTreeSet::new();
        let mut current_groups: BTreeMap<usize, BTreeSet<String>> = groups.clone();

        while !current_groups.is_empty() {
            let mut new_groups: BTreeMap<usize, BTreeSet<String>> = BTreeMap::new();
            let mut used: BTreeSet<String> = BTreeSet::new();
            let keys: Vec<usize> = current_groups.keys().cloned().collect();

            for &i in &keys {
                if let Some(next) = current_groups.get(&(i + 1)) {
                    for a in &current_groups[&i] {
                        for b in next {
                            if Self::can_combine(a, b) {
                                let combined = Self::combine(a, b);
                                let ones = Self::count_ones(&combined);
                                new_groups.entry(ones).or_default().insert(combined.clone());
                                used.insert(a.clone());
                                used.insert(b.clone());
                            }
                        }
                    }
                }
            }

            for (i, set) in &current_groups {
                for s in set {
                    if !used.contains(s) {
                        prime_implicants.insert(s.clone());
                    }
                }
            }

            if new_groups.is_empty() {
                break;
            }
            current_groups = new_groups;
        }

        prime_implicants.into_iter().collect()
    }

    pub fn cover_table(&self, implicants: &[String]) -> BTreeMap<usize, BTreeSet<usize>> {
        let mut table: BTreeMap<usize, BTreeSet<usize>> = BTreeMap::new();

        for &m in &self.minterms {
            let mut covering = BTreeSet::new();
            for (i, imp) in implicants.iter().enumerate() {
                if self.minterm_covers(m, imp) {
                    covering.insert(i);
                }
            }
            table.insert(m, covering);
        }
        table
    }

    fn minterm_covers(&self, minterm: usize, implicant: &str) -> bool {
        let bin = Self::to_binary_string(minterm, self.num_vars);
        for (c1, c2) in bin.chars().zip(implicant.chars()) {
            if c2 != '-' && c1 != c2 {
                return false;
            }
        }
        true
    }

    pub fn essential_implicants(&self, implicants: &[String]) -> Vec<usize> {
        let table = self.cover_table(implicants);
        let mut essential: Vec<usize> = Vec::new();
        let mut remaining_mintrms: BTreeSet<usize> = self.minterms.iter().cloned().collect();

        for (&m, covering) in &table {
            if covering.len() == 1 {
                let imp_idx = *covering.iter().next().unwrap();
                if !essential.contains(&imp_idx) {
                    essential.push(imp_idx);
                }
            }
        }

        essential.sort();
        essential
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_binary_string() {
        assert_eq!(QuineMcCluskey::to_binary_string(5, 4), "0101");
    }

    #[test]
    fn test_count_ones() {
        assert_eq!(QuineMcCluskey::count_ones("0101"), 2);
    }

    #[test]
    fn test_can_combine() {
        assert!(QuineMcCluskey::can_combine("0101", "0100"));
        assert!(QuineMcCluskey::can_combine("0101", "1101"));
    }

    #[test]
    fn test_combine() {
        assert_eq!(QuineMcCluskey::combine("0101", "0100"), "010-");
    }

    #[test]
    fn test_minimize_2var() {
        let mut qm = QuineMcCluskey::new(2);
        qm.add_minterm(0);
        qm.add_minterm(1);
        qm.add_minterm(2);
        let implicants = qm.minimize();
        assert!(!implicants.is_empty());
    }

    #[test]
    fn test_minimize_3var() {
        let mut qm = QuineMcCluskey::new(3);
        qm.add_minterm(0);
        qm.add_minterm(1);
        qm.add_minterm(2);
        qm.add_minterm(3);
        qm.add_minterm(4);
        qm.add_minterm(5);
        qm.add_minterm(6);
        qm.add_minterm(7);
        let implicants = qm.minimize();
        assert!(implicants.is_empty());
    }

    #[test]
    fn test_minimize_with_dont_care() {
        let mut qm = QuineMcCluskey::new(3);
        qm.add_minterm(0);
        qm.add_minterm(2);
        qm.add_dont_care(1);
        let implicants = qm.minimize();
        assert!(!implicants.is_empty());
    }

    #[test]
    fn test_cover_table() {
        let mut qm = QuineMcCluskey::new(2);
        qm.add_minterm(0);
        qm.add_minterm(1);
        qm.add_minterm(2);
        qm.add_minterm(3);
        let implicants = qm.minimize();
        let table = qm.cover_table(&implicants);
        assert!(!table.is_empty());
    }

    #[test]
    fn test_essential_implicants() {
        let mut qm = QuineMcCluskey::new(3);
        qm.add_minterm(0);
        qm.add_minterm(1);
        qm.add_minterm(2);
        qm.add_minterm(5);
        qm.add_minterm(7);
        let implicants = qm.minimize();
        let essential = qm.essential_implicants(&implicants);
        assert!(!essential.is_empty());
    }
}