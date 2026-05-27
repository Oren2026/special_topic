use std::collections::{HashMap, BTreeSet, VecDeque};

#[derive(Debug, Clone)]
pub struct Cell {
    pub name: String,
    pub area: f64,
    pub delay: f64,
    pub inputs: Vec<String>,
    pub output: String,
    pub function: String,
}

impl Cell {
    pub fn new(name: &str, area: f64, delay: f64, inputs: Vec<String>, output: &str, function: &str) -> Self {
        Cell {
            name: name.to_string(),
            area,
            delay,
            inputs,
            output: output.to_string(),
            function: function.to_string(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Library {
    pub cells: HashMap<String, Cell>,
}

impl Library {
    pub fn new() -> Self {
        Library { cells: HashMap::new() }
    }

    pub fn add_cell(&mut self, cell: Cell) {
        self.cells.insert(cell.name.clone(), cell);
    }

    pub fn standard_cells() -> Self {
        let mut lib = Library::new();
        lib.add_cell(Cell::new("AND2", 2.0, 1.0, vec!["A".to_string(), "B".to_string()], "Y", "A & B"));
        lib.add_cell(Cell::new("OR2", 2.0, 1.0, vec!["A".to_string(), "B".to_string()], "Y", "A | B"));
        lib.add_cell(Cell::new("NOT", 1.0, 0.5, vec!["A".to_string()], "Y", "!A"));
        lib.add_cell(Cell::new("NAND2", 1.5, 0.8, vec!["A".to_string(), "B".to_string()], "Y", "!(A & B)"));
        lib.add_cell(Cell::new("NOR2", 1.5, 0.8, vec!["A".to_string(), "B".to_string()], "Y", "!(A | B)"));
        lib.add_cell(Cell::new("XOR2", 3.0, 1.5, vec!["A".to_string(), "B".to_string()], "Y", "A ^ B"));
        lib.add_cell(Cell::new("MUX2", 4.0, 1.2, vec!["A".to_string(), "B".to_string(), "S".to_string()], "Y", "(A & !S) | (B & S)"));
        lib.add_cell(Cell::new("DFF", 6.0, 2.0, vec!["D".to_string(), "CLK".to_string()], "Q", "D register"));
        lib
    }
}

pub struct TechMapper {
    library: Library,
}

impl TechMapper {
    pub fn new(library: Library) -> Self {
        TechMapper { library }
    }

    pub fn map(&self, netlist: &Netlist) -> MappingResult {
        let mut total_area = 0.0;
        let mut total_delay = 0.0;
        let mut instances: Vec<Instance> = Vec::new();

        for node in &netlist.nodes {
            if let Some(cell) = self.find_matching_cell(&node.function) {
                total_area += cell.area;
                total_delay += cell.delay;
                instances.push(Instance {
                    cell_name: cell.name.clone(),
                    inputs: node.inputs.clone(),
                    output: node.output.clone(),
                });
            }
        }

        MappingResult {
            instances,
            total_area,
            total_delay,
        }
    }

    fn find_matching_cell(&self, function: &str) -> Option<&Cell> {
        for cell in self.library.cells.values() {
            if cell.function == function {
                return Some(cell);
            }
        }
        self.library.cells.values().find(|c| c.name.starts_with("AND")).or(None)
    }
}

#[derive(Debug, Clone)]
pub struct Netlist {
    pub nodes: Vec<NetlistNode>,
}

#[derive(Debug, Clone)]
pub struct NetlistNode {
    pub id: usize,
    pub function: String,
    pub inputs: Vec<String>,
    pub output: String,
}

impl Netlist {
    pub fn new() -> Self {
        Netlist { nodes: Vec::new() }
    }

    pub fn add_node(&mut self, function: String, inputs: Vec<String>, output: String) {
        let id = self.nodes.len();
        self.nodes.push(NetlistNode { id, function, inputs, output });
    }
}

#[derive(Debug)]
pub struct MappingResult {
    pub instances: Vec<Instance>,
    pub total_area: f64,
    pub total_delay: f64,
}

#[derive(Debug)]
pub struct Instance {
    pub cell_name: String,
    pub inputs: Vec<String>,
    pub output: String,
}

pub fn dfoa(netlist: &Netlist) -> Vec<String> {
    let mut order: Vec<String> = Vec::new();
    let mut visited: BTreeSet<usize> = BTreeSet::new();
    for node in &netlist.nodes {
        if !visited.contains(&node.id) {
            dfs(node.id, netlist, &mut visited, &mut order);
        }
    }
    order
}

fn dfs(node_id: usize, netlist: &Netlist, visited: &mut BTreeSet<usize>, order: &mut Vec<String>) {
    visited.insert(node_id);
    if let Some(node) = netlist.nodes.iter().find(|n| n.id == node_id) {
        for input in &node.inputs {
            if let Some(dep) = netlist.nodes.iter().find(|n| n.output == *input) {
                if !visited.contains(&dep.id) {
                    dfs(dep.id, netlist, visited, order);
                }
            }
        }
        order.push(node.output.clone());
    }
}

pub fn lfoa(netlist: &Netlist) -> Vec<String> {
    let mut order: Vec<String> = Vec::new();
    let mut in_degree: HashMap<String, usize> = HashMap::new();

    for node in &netlist.nodes {
        *in_degree.entry(node.output.clone()).or_insert(0);
        for input in &node.inputs {
            *in_degree.entry(input.clone()).or_insert(0) += 1;
        }
    }

    let mut queue: VecDeque<String> = in_degree.iter()
        .filter(|(_, &d)| d == 0)
        .map(|(n, _)| n.clone())
        .collect();

    while let Some(name) = queue.pop_front() {
        order.push(name.clone());
        if let Some(node) = netlist.nodes.iter().find(|n| n.output == name) {
            for input in &node.inputs {
                if let Some(d) = in_degree.get_mut(input) {
                    *d -= 1;
                    if *d == 0 {
                        queue.push_back(input.clone());
                    }
                }
            }
        }
    }

    order
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_library_creation() {
        let lib = Library::new();
        assert!(lib.cells.is_empty());
    }

    #[test]
    fn test_standard_cells() {
        let lib = Library::standard_cells();
        assert!(lib.cells.len() >= 5);
        assert!(lib.cells.contains_key("AND2"));
        assert!(lib.cells.contains_key("OR2"));
        assert!(lib.cells.contains_key("NOT"));
    }

    #[test]
    fn test_netlist_creation() {
        let mut netlist = Netlist::new();
        netlist.add_node("A & B".to_string(), vec!["a".to_string(), "b".to_string()], "y".to_string());
        assert_eq!(netlist.nodes.len(), 1);
    }

    #[test]
    fn test_tech_mapper() {
        let lib = Library::standard_cells();
        let mapper = TechMapper::new(lib);
        let mut netlist = Netlist::new();
        netlist.add_node("A & B".to_string(), vec!["a".to_string(), "b".to_string()], "y".to_string());
        let result = mapper.map(&netlist);
        assert!(!result.instances.is_empty());
    }

    #[test]
    fn test_dfoa() {
        let mut netlist = Netlist::new();
        netlist.add_node("A & B".to_string(), vec!["a".to_string(), "b".to_string()], "y".to_string());
        let order = dfoa(&netlist);
        assert!(!order.is_empty());
    }

    #[test]
    fn test_lfoa() {
        let mut netlist = Netlist::new();
        netlist.add_node("A & B".to_string(), vec!["a".to_string(), "b".to_string()], "y".to_string());
        netlist.add_node("Y | C".to_string(), vec!["y".to_string(), "c".to_string()], "z".to_string());
        let order = lfoa(&netlist);
        assert!(!order.is_empty());
    }
}