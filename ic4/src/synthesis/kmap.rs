use std::collections::{HashSet, BTreeSet};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Minterm {
    pub vars: Vec<bool>,
    pub is_dc: bool,
}

impl Minterm {
    pub fn new(vars: Vec<bool>) -> Self {
        Minterm { vars, is_dc: false }
    }

    pub fn dc(vars: Vec<bool>) -> Self {
        Minterm { vars, is_dc: true }
    }

    pub fn value(&self) -> usize {
        self.vars.iter().fold(0, |acc, &b| (acc << 1) | (b as usize))
    }

    pub fn ones_count(&self) -> usize {
        self.vars.iter().filter(|&&b| b).count()
    }
}

pub struct Kmap {
    pub vars: Vec<String>,
    pub minterms: Vec<Minterm>,
    pub n: usize,
}

impl Kmap {
    pub fn new(vars: Vec<String>, minterms: Vec<Minterm>) -> Self {
        let n = vars.len();
        Kmap { vars, minterms, n }
    }

    pub fn gray_code(n: usize) -> Vec<String> {
        let mut code = Vec::with_capacity(1 << n);
        for i in 0..(1 << n) {
            let g = i ^ (i >> 1);
            code.push(format!("{:0n$b}", g, n = n));
        }
        code
    }

    pub fn find_pairs(&self) -> Vec<(Minterm, Minterm)> {
        let mut pairs = Vec::new();
        for (i, m1) in self.minterms.iter().enumerate() {
            if m1.is_dc { continue; }
            for m2 in &self.minterms[i+1..] {
                if m2.is_dc { continue; }
                if self.can_group(m1, m2) {
                    pairs.push((m1.clone(), m2.clone()));
                }
            }
        }
        pairs
    }

    fn can_group(&self, m1: &Minterm, m2: &Minterm) -> bool {
        if m1.vars.len() != m2.vars.len() { return false; }
        let diffs: Vec<usize> = m1.vars.iter()
            .zip(m2.vars.iter())
            .enumerate()
            .filter(|(_, (a, b))| a != b)
            .map(|(i, _)| i)
            .collect();
        diffs.len() == 1
    }

    pub fn group_size(&self, minterms: &[Minterm]) -> usize {
        if minterms.is_empty() { return 0; }
        minterms[0].vars.len()
    }

    pub fn simplify(&self) -> Vec<Minterm> {
        let mut groups: Vec<Vec<Minterm>> = vec![Vec::new(); self.n + 1];
        for m in &self.minterms {
            if !m.is_dc {
                groups[m.ones_count()].push(m.clone());
            }
        }
        let mut prime_implicants: Vec<Minterm> = Vec::new();
        let mut visited: HashSet<Vec<bool>> = HashSet::new();

        for (i, group) in groups.iter().enumerate() {
            for m in group {
                if visited.contains(&m.vars) { continue; }
                let mut current = m.clone();
                loop {
                    let mut next_group_idx = current.ones_count() + 1;
                    if next_group_idx >= groups.len() { break; }
                    let mut found = false;
                    for other in &groups[next_group_idx] {
                        if other.is_dc || visited.contains(&other.vars) { continue; }
                        if self.can_group(&current, other) {
                            let merged = self.merge(&current, other);
                            if !visited.contains(&merged.vars) {
                                visited.insert(current.vars.clone());
                                current = merged;
                                found = true;
                                break;
                            }
                        }
                    }
                    if !found { break; }
                }
                if !visited.contains(&current.vars) {
                    visited.insert(current.vars.clone());
                    prime_implicants.push(current);
                }
            }
        }

        if prime_implicants.is_empty() {
            for m in &self.minterms {
                if !m.is_dc {
                    return vec![m.clone()];
                }
            }
        }
        prime_implicants
    }

    fn merge(&self, m1: &Minterm, m2: &Minterm) -> Minterm {
        let mut result = Vec::new();
        for (a, b) in m1.vars.iter().zip(m2.vars.iter()) {
            if a == b {
                result.push(*a);
            } else {
                result.push(false);
            }
        }
        Minterm::new(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_minterm_value() {
        let m = Minterm::new(vec![false, true, false, true]);
        assert_eq!(m.value(), 5);
    }

    #[test]
    fn test_ones_count() {
        let m = Minterm::new(vec![true, false, true, true]);
        assert_eq!(m.ones_count(), 3);
    }

    #[test]
    fn test_gray_code_2() {
        let code = Kmap::gray_code(2);
        assert_eq!(code, vec!["00", "01", "11", "10"]);
    }

    #[test]
    fn test_kmap_simplify_2var() {
        let vars = vec!["A".to_string(), "B".to_string()];
        let minterms = vec![
            Minterm::new(vec![false, false]),
            Minterm::new(vec![false, true]),
            Minterm::new(vec![true, true]),
        ];
        let kmap = Kmap::new(vars, minterms);
        let primes = kmap.simplify();
        assert!(!primes.is_empty());
    }

    #[test]
    fn test_kmap_simplify_3var() {
        let vars = vec!["A".to_string(), "B".to_string(), "C".to_string()];
        let minterms = vec![
            Minterm::new(vec![false, false, false]),
            Minterm::new(vec![false, false, true]),
            Minterm::new(vec![false, true, false]),
            Minterm::new(vec![true, false, false]),
            Minterm::new(vec![true, false, true]),
            Minterm::new(vec![true, true, false]),
        ];
        let kmap = Kmap::new(vars, minterms);
        let primes = kmap.simplify();
        assert!(!primes.is_empty());
    }
}