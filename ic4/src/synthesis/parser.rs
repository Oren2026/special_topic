use crate::Signal;
use std::collections::HashSet;

/// Simple recursive descent parser for boolean expressions.
/// Grammar:
///   expr     → term (( "&" | "|" ) term)*
///   term     → factor
///   factor   → "!" factor | "(" expr ")" | VAR
///   VAR      → [a-zA-Z_][a-zA-Z0-9_]*

#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
enum Token {
    Var(String),
    Not,
    And,
    Or,
    LParen,
    RParen,
    End,
}

struct Lexer {
    input: Vec<char>,
    pos: usize,
}

impl Lexer {
    fn new(input: &str) -> Self {
        Lexer { input: input.chars().collect(), pos: 0 }
    }

    fn peek(&self) -> Option<char> {
        self.input.get(self.pos).copied()
    }

    fn advance(&mut self) -> Option<char> {
        let ch = self.input.get(self.pos).copied();
        self.pos += 1;
        ch
    }

    fn skip_whitespace(&mut self) {
        while let Some(ch) = self.peek() {
            if ch.is_whitespace() {
                self.advance();
            } else {
                break;
            }
        }
    }

    fn read_ident(&mut self) -> String {
        let mut result = String::new();
        while let Some(ch) = self.peek() {
            if ch.is_alphanumeric() || ch == '_' {
                result.push(self.advance().unwrap());
            } else {
                break;
            }
        }
        result
    }

    fn next_token(&mut self) -> Token {
        self.skip_whitespace();
        match self.advance() {
            None => Token::End,
            Some('!') => Token::Not,
            Some('&') => Token::And,
            Some('|') => Token::Or,
            Some('(') => Token::LParen,
            Some(')') => Token::RParen,
            Some(ch) if ch.is_alphabetic() || ch == '_' => {
                let mut s = String::from(ch);
                while let Some(c) = self.peek() {
                    if c.is_alphanumeric() || c == '_' {
                        s.push(self.advance().unwrap());
                    } else {
                        break;
                    }
                }
                Token::Var(s)
            }
            _ => self.next_token(),
        }
    }
}

struct Parser {
    lexer: Lexer,
    current: Token,
}

impl Parser {
    fn new(input: &str) -> Self {
        let mut lexer = Lexer::new(input);
        let current = lexer.next_token();
        Parser { lexer, current }
    }

    fn advance(&mut self) -> Token {
        let prev = self.current.clone();
        self.current = self.lexer.next_token();
        prev
    }

    fn expect(&mut self, expected: &Token) -> bool {
        if &self.current == expected {
            self.advance();
            true
        } else {
            false
        }
    }

    fn parse(&mut self) -> Result<Signal, String> {
        let expr = self.parse_expr()?;
        if self.current != Token::End {
            return Err(format!("Unexpected token: {:?}", self.current));
        }
        Ok(expr)
    }

    // expr → term (( "&" | "|" ) term)*
    fn parse_expr(&mut self) -> Result<Signal, String> {
        let mut left = self.parse_term()?;
        loop {
            match &self.current {
                Token::And => {
                    self.advance();
                    let right = self.parse_term()?;
                    left = left.and(right);
                }
                Token::Or => {
                    self.advance();
                    let right = self.parse_term()?;
                    left = left.or(right);
                }
                _ => break,
            }
        }
        Ok(left)
    }

    // term → factor
    fn parse_term(&mut self) -> Result<Signal, String> {
        self.parse_factor()
    }

    // factor → "!" factor | "(" expr ")" | VAR
    fn parse_factor(&mut self) -> Result<Signal, String> {
        match self.current.clone() {
            Token::Not => {
                self.advance();
                let inner = self.parse_factor()?;
                Ok(inner.not())
            }
            Token::LParen => {
                self.advance();
                let inner = self.parse_expr()?;
                if self.expect(&Token::RParen) {
                    Ok(inner)
                } else {
                    Err("Expected ')'".to_string())
                }
            }
            Token::Var(ref name) => {
                self.advance();
                let name = name.clone();
                // Lowercase '0'/'1' mean const 0/1, 'a'/'A' etc mean variables
                match name.as_str() {
                    "0" => Ok(Signal::Const0),
                    "1" => Ok(Signal::Const1),
                    _ => Ok(Signal::var(&name)),
                }
            }
            Token::End => Err("Unexpected end of expression".to_string()),
            _ => Err(format!("Unexpected token: {:?}", self.current)),
        }
    }
}

/// Parse a boolean expression string into a Signal AST.
/// Operators: `&` (AND), `|` (OR), `!` (NOT)
/// Examples: "a & b", "a | !b", "(a & b) | c", "a & b | c"
pub fn parse_signal(input: &str) -> Result<Signal, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("Empty expression".to_string());
    }
    let mut parser = Parser::new(trimmed);
    parser.parse()
}

/// Collect all variable names from an expression
pub fn get_vars(signal: &Signal) -> HashSet<String> {
    let mut vars = HashSet::new();
    collect_vars(signal, &mut vars);
    vars
}

fn collect_vars(signal: &Signal, vars: &mut HashSet<String>) {
    match signal {
        Signal::Var(name) => { vars.insert(name.clone()); }
        Signal::Not(inner) => collect_vars(inner, vars),
        Signal::And(set) | Signal::Or(set) => {
            for s in set {
                collect_vars(s, vars);
            }
        }
        Signal::Const0 | Signal::Const1 => {}
    }
}

/// Evaluate a signal given a mapping of variable names to boolean values
fn eval_signal(signal: &Signal, values: &HashSet<String>) -> bool {
    match signal {
        Signal::Const0 => false,
        Signal::Const1 => true,
        Signal::Var(name) => values.contains(name),
        Signal::Not(inner) => !eval_signal(inner, values),
        Signal::And(set) => set.iter().all(|s| eval_signal(s, values)),
        Signal::Or(set) => set.iter().any(|s| eval_signal(s, values)),
    }
}

/// Derive minterms from a signal expression by evaluating all 2^n input combinations.
/// Returns the set of minterm indices where the expression evaluates to true.
pub fn derive_minterms(signal: &Signal) -> Result<Vec<usize>, String> {
    let vars = get_vars(signal);
    let var_list: Vec<String> = vars.into_iter().collect();
    let n = var_list.len();

    if n > 16 {
        return Err("Too many variables (max 16)".to_string());
    }

    let mut minterms = Vec::new();

    for i in 0..(1 << n) {
        let mut values = HashSet::new();
        for (j, var) in var_list.iter().enumerate() {
            if (i >> j) & 1 == 1 {
                values.insert(var.clone());
            }
        }
        if eval_signal(signal, &values) {
            minterms.push(i);
        }
    }

    Ok(minterms)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_var() {
        let s = parse_signal("a").unwrap();
        assert_eq!(s, Signal::Var("a".to_string()));
    }

    #[test]
    fn test_parse_and() {
        let s = parse_signal("a & b").unwrap();
        match s {
            Signal::And(set) if set.len() == 2 => {},
            other => panic!("Expected And({{a, b}}), got {:?}", other),
        }
    }

    #[test]
    fn test_parse_or() {
        let s = parse_signal("a | b").unwrap();
        match s {
            Signal::Or(set) if set.len() == 2 => {},
            other => panic!("Expected Or({{a, b}}), got {:?}", other),
        }
    }

    #[test]
    fn test_parse_not() {
        let s = parse_signal("!a").unwrap();
        match s {
            Signal::Not(inner) => {
                match *inner {
                    Signal::Var(ref name) if name == "a" => {},
                    other => panic!("Expected Not(Var(a)), got {:?}", other),
                }
            }
            other => panic!("Expected Not, got {:?}", other),
        }
    }

    #[test]
    fn test_parse_complex() {
        let s = parse_signal("a & b | c").unwrap();
        // a & b | c = Or(And({a, b}), Var(c))
        match s {
            Signal::Or(set) if set.len() == 2 => {},
            other => panic!("Expected Or with 2 elements, got {:?}", other),
        }
    }

    #[test]
    fn test_derive_minterms_simple() {
        // a
        let s = Signal::var("a");
        let mins = derive_minterms(&s).unwrap();
        assert_eq!(mins, vec![1]); // only a=1 (binary 01)
    }

    #[test]
    fn test_derive_minterms_and() {
        // a & b → only 11 = 3
        let s = Signal::var("a").and(Signal::var("b"));
        let mins = derive_minterms(&s).unwrap();
        assert_eq!(mins, vec![3]); // a=1, b=1 (binary 11)
    }

    #[test]
    fn test_derive_minterms_or() {
        // a | b → 01, 10, 11 = 1, 2, 3
        let s = Signal::var("a").or(Signal::var("b"));
        let mins = derive_minterms(&s).unwrap();
        assert_eq!(mins, vec![1, 2, 3]);
    }

    #[test]
    fn test_derive_minterms_not() {
        // !a → 0 = 0
        let s = Signal::var("a").not();
        let mins = derive_minterms(&s).unwrap();
        assert_eq!(mins, vec![0]); // a=0
    }

    #[test]
    fn test_derive_minterms Expression() {
        // a & b | c with vars a=bit0, b=bit1, c=bit2
        // a&b|c = 100 | 001 | 010 = 1, 2, 4 -> since bits are A=bit0, B=bit1, C=bit2
        let s = parse_signal("a & b | c").unwrap();
        let mins = derive_minterms(&s).unwrap();
        // a&b = 11 (a=1,b=1) = 3, c = 100 (c=1) = 4
        // Actually: a&b|c = minterms 1,2,4,5,6,7?
        // Let's trace: ab|c with A=a(bit0), B=b(bit1), C=c(bit2)
        // ab|c = 1(001) when a=1,b=0,c=0 or ab=1 when a=1,b=1,c=0 or c=1
        // Wait, the evaluation: (a AND b) OR c
        // For 3 vars (a,b,c): bit0=a, bit1=b, bit2=c
        // ab evaluates when a&b=1 (a=1,b=1 regardless of c) → mins 4,5,6,7 with c varies
        // Actually minterm index: bit2=c(4), bit1=b(2), bit0=a(1)
        // ab = 1 when (a=1,b=1) with c anywhere → c=0 (4+0=4) or c=1 (4+1=5)? Wait no
        // Let me reconsider: 3-bit representation with a=LSD(bit0), b=bit1, c=MSD(bit2)
        // ab gives 1 when a=1,b=1 so index 3 (011) and 7 (111) since c doesn't matter
        // So ab minterms are 3,7
        // c gives 1 when c=1 so indices 4 (100),5 (101),6 (110),7 (111)
        // ab|c = {3,4,5,6,7} = 3,4,5,6,7
        assert_eq!(mins, vec![3, 4, 5, 6, 7]);
    }
}
