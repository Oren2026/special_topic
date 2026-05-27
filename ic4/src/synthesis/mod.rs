pub mod kmap;
pub mod quine;
pub mod techmap;

pub use kmap::{Kmap, Minterm};
pub use quine::QuineMcCluskey;
pub use techmap::{Library, Cell, TechMapper};

use std::collections::BTreeSet;

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Signal {
    Const0,
    Const1,
    Var(String),
    Not(Box<Signal>),
    And(BTreeSet<Signal>),
    Or(BTreeSet<Signal>),
}

impl Signal {
    pub fn var(name: &str) -> Self {
        Signal::Var(name.to_string())
    }

    pub fn and(self, other: Signal) -> Self {
        let mut set = BTreeSet::new();
        match self {
            Signal::And(mut s) => { set.append(&mut s); }
            s => { set.insert(s); }
        }
        match other {
            Signal::And(mut s) => { set.append(&mut s); }
            s => { set.insert(s); }
        }
        Signal::And(set)
    }

    pub fn or(self, other: Signal) -> Self {
        let mut set = BTreeSet::new();
        match self {
            Signal::Or(mut s) => { set.append(&mut s); }
            s => { set.insert(s); }
        }
        match other {
            Signal::Or(mut s) => { set.append(&mut s); }
            s => { set.insert(s); }
        }
        Signal::Or(set)
    }

    pub fn not(self) -> Self {
        match self {
            Signal::Not(s) => *s,
            s => Signal::Not(Box::new(s)),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_signal_and() {
        let a = Signal::var("a");
        let b = Signal::var("b");
        let ab = a.and(b);
        match ab {
            Signal::And(ref set) if set.len() == 2 => {},
            _ => panic!("Expected And with 2 elements"),
        }
    }

    #[test]
    fn test_signal_or() {
        let a = Signal::var("a");
        let b = Signal::var("b");
        let ab = a.or(b);
        match ab {
            Signal::Or(ref set) if set.len() == 2 => {},
            _ => panic!("Expected Or with 2 elements"),
        }
    }

    #[test]
    fn test_signal_not() {
        let a = Signal::var("a");
        let na = a.not();
        match na {
            Signal::Not(_) => {},
            _ => panic!("Expected Not"),
        }
    }
}