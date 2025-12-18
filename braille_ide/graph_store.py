"""
SAL Braille IDE Graph Storage Layer

Graph-based storage for the braille IDE. Supports:
- NetworkX + SQLite (lightweight, default)
- Neo4j (production, optional)

Everything is a node or relationship:
- Projects, Files, Functions, Classes
- SAL Tasks, Steps, Conversations
- Braille cells, Semantic concepts

⠛⠗⠁⠏⠓_⠎⠞⠕⠗⠑
"""

import json
import sqlite3
import os
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
import hashlib

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from braille8_core import Braille8Encoder, text_to_braille8


class NodeType(str, Enum):
    """Types of nodes in the graph"""
    PROJECT = "Project"
    FILE = "File"
    FUNCTION = "Function"
    CLASS = "Class"
    VARIABLE = "Variable"
    IMPORT = "Import"
    TASK = "Task"
    STEP = "Step"
    CONVERSATION = "Conversation"
    BRAILLE_CELL = "BrailleCell"
    SEMANTIC_CONCEPT = "SemanticConcept"
    USER = "User"


class RelationType(str, Enum):
    """Types of relationships in the graph"""
    CONTAINS = "CONTAINS"
    IMPORTS = "IMPORTS"
    DEFINES = "DEFINES"
    CALLS = "CALLS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    REFERENCES = "REFERENCES"
    HAS_STEP = "HAS_STEP"
    GENERATED = "GENERATED"
    SPAWNED = "SPAWNED"
    CLARIFIED_BY = "CLARIFIED_BY"
    BRAILLE_ENCODED = "BRAILLE_ENCODED"
    MEANS = "MEANS"
    NEXT = "NEXT"
    CREATED_BY = "CREATED_BY"


@dataclass
class Node:
    """A node in the graph"""
    id: str
    type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)
    braille_id: str = ""
    
    def __post_init__(self):
        if not self.braille_id:
            encoder = Braille8Encoder()
            self.braille_id = encoder.encode(self.id[:8])
            
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "properties": self.properties,
            "braille_id": self.braille_id
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Node':
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            properties=data.get("properties", {}),
            braille_id=data.get("braille_id", "")
        )


@dataclass
class Relationship:
    """A relationship between nodes"""
    id: str
    type: RelationType
    source_id: str
    target_id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "properties": self.properties
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Relationship':
        return cls(
            id=data["id"],
            type=RelationType(data["type"]),
            source_id=data["source_id"],
            target_id=data["target_id"],
            properties=data.get("properties", {})
        )


class GraphStore(ABC):
    """Abstract base class for graph storage"""
    
    @abstractmethod
    def create_node(self, node: Node) -> Node:
        """Create a node"""
        pass
        
    @abstractmethod
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID"""
        pass
        
    @abstractmethod
    def update_node(self, node: Node) -> Node:
        """Update a node"""
        pass
        
    @abstractmethod
    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships"""
        pass
        
    @abstractmethod
    def create_relationship(self, rel: Relationship) -> Relationship:
        """Create a relationship"""
        pass
        
    @abstractmethod
    def get_relationships(self, node_id: str, rel_type: RelationType = None, 
                          direction: str = "both") -> List[Relationship]:
        """Get relationships for a node"""
        pass
        
    @abstractmethod
    def delete_relationship(self, rel_id: str) -> bool:
        """Delete a relationship"""
        pass
        
    @abstractmethod
    def query_nodes(self, node_type: NodeType = None, 
                    properties: Dict[str, Any] = None) -> List[Node]:
        """Query nodes by type and properties"""
        pass
        
    @abstractmethod
    def traverse(self, start_id: str, rel_types: List[RelationType] = None,
                 max_depth: int = 3) -> List[Tuple[Node, List[Relationship]]]:
        """Traverse the graph from a starting node"""
        pass


class NetworkXSQLiteStore(GraphStore):
    """
    Lightweight graph store using NetworkX for in-memory operations
    and SQLite for persistence.
    
    No external dependencies beyond Python stdlib + networkx.
    """
    
    def __init__(self, db_path: str = None):
        if not HAS_NETWORKX:
            raise ImportError("NetworkX is required. Install with: pip install networkx")
            
        self.db_path = db_path or os.path.expanduser("~/.sal-braille-ide/graph.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.graph = nx.DiGraph()
        self.encoder = Braille8Encoder()
        
        self._init_db()
        self._load_from_db()
        
    def _init_db(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                properties TEXT,
                braille_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                properties TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES nodes(id),
                FOREIGN KEY (target_id) REFERENCES nodes(id)
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rels_source ON relationships(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rels_target ON relationships(target_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_rels_type ON relationships(type)')
        
        conn.commit()
        conn.close()
        
    def _load_from_db(self):
        """Load graph from SQLite into NetworkX"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load nodes
        cursor.execute('SELECT id, type, properties, braille_id FROM nodes')
        for row in cursor.fetchall():
            node_id, node_type, props_json, braille_id = row
            props = json.loads(props_json) if props_json else {}
            self.graph.add_node(node_id, 
                               type=node_type, 
                               properties=props,
                               braille_id=braille_id)
            
        # Load relationships
        cursor.execute('SELECT id, type, source_id, target_id, properties FROM relationships')
        for row in cursor.fetchall():
            rel_id, rel_type, source_id, target_id, props_json = row
            props = json.loads(props_json) if props_json else {}
            if source_id in self.graph and target_id in self.graph:
                self.graph.add_edge(source_id, target_id,
                                   id=rel_id,
                                   type=rel_type,
                                   properties=props)
                                   
        conn.close()
        
    def _save_node(self, node: Node):
        """Save node to SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO nodes (id, type, properties, braille_id, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (node.id, node.type.value, json.dumps(node.properties), node.braille_id))
        
        conn.commit()
        conn.close()
        
    def _save_relationship(self, rel: Relationship):
        """Save relationship to SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO relationships (id, type, source_id, target_id, properties)
            VALUES (?, ?, ?, ?, ?)
        ''', (rel.id, rel.type.value, rel.source_id, rel.target_id, json.dumps(rel.properties)))
        
        conn.commit()
        conn.close()
        
    def create_node(self, node: Node) -> Node:
        """Create a node"""
        self.graph.add_node(node.id,
                           type=node.type.value,
                           properties=node.properties,
                           braille_id=node.braille_id)
        self._save_node(node)
        return node
        
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID"""
        if node_id not in self.graph:
            return None
            
        data = self.graph.nodes[node_id]
        return Node(
            id=node_id,
            type=NodeType(data.get('type', 'File')),
            properties=data.get('properties', {}),
            braille_id=data.get('braille_id', '')
        )
        
    def update_node(self, node: Node) -> Node:
        """Update a node"""
        if node.id in self.graph:
            self.graph.nodes[node.id]['type'] = node.type.value
            self.graph.nodes[node.id]['properties'] = node.properties
            self.graph.nodes[node.id]['braille_id'] = node.braille_id
            self._save_node(node)
        return node
        
    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its relationships"""
        if node_id not in self.graph:
            return False
            
        self.graph.remove_node(node_id)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM nodes WHERE id = ?', (node_id,))
        cursor.execute('DELETE FROM relationships WHERE source_id = ? OR target_id = ?', 
                      (node_id, node_id))
        conn.commit()
        conn.close()
        
        return True
        
    def create_relationship(self, rel: Relationship) -> Relationship:
        """Create a relationship"""
        if rel.source_id not in self.graph or rel.target_id not in self.graph:
            raise ValueError(f"Both source and target nodes must exist")
            
        self.graph.add_edge(rel.source_id, rel.target_id,
                           id=rel.id,
                           type=rel.type.value,
                           properties=rel.properties)
        self._save_relationship(rel)
        return rel
        
    def get_relationships(self, node_id: str, rel_type: RelationType = None,
                          direction: str = "both") -> List[Relationship]:
        """Get relationships for a node"""
        if node_id not in self.graph:
            return []
            
        relationships = []
        
        # Outgoing
        if direction in ("out", "both"):
            for target in self.graph.successors(node_id):
                edge_data = self.graph.edges[node_id, target]
                if rel_type is None or edge_data.get('type') == rel_type.value:
                    relationships.append(Relationship(
                        id=edge_data.get('id', f"{node_id}->{target}"),
                        type=RelationType(edge_data.get('type', 'CONTAINS')),
                        source_id=node_id,
                        target_id=target,
                        properties=edge_data.get('properties', {})
                    ))
                    
        # Incoming
        if direction in ("in", "both"):
            for source in self.graph.predecessors(node_id):
                edge_data = self.graph.edges[source, node_id]
                if rel_type is None or edge_data.get('type') == rel_type.value:
                    relationships.append(Relationship(
                        id=edge_data.get('id', f"{source}->{node_id}"),
                        type=RelationType(edge_data.get('type', 'CONTAINS')),
                        source_id=source,
                        target_id=node_id,
                        properties=edge_data.get('properties', {})
                    ))
                    
        return relationships
        
    def delete_relationship(self, rel_id: str) -> bool:
        """Delete a relationship"""
        # Find edge with this ID
        for u, v, data in self.graph.edges(data=True):
            if data.get('id') == rel_id:
                self.graph.remove_edge(u, v)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM relationships WHERE id = ?', (rel_id,))
                conn.commit()
                conn.close()
                
                return True
        return False
        
    def query_nodes(self, node_type: NodeType = None,
                    properties: Dict[str, Any] = None) -> List[Node]:
        """Query nodes by type and properties"""
        results = []
        
        for node_id in self.graph.nodes():
            data = self.graph.nodes[node_id]
            
            # Filter by type
            if node_type and data.get('type') != node_type.value:
                continue
                
            # Filter by properties
            if properties:
                node_props = data.get('properties', {})
                match = all(node_props.get(k) == v for k, v in properties.items())
                if not match:
                    continue
                    
            results.append(Node(
                id=node_id,
                type=NodeType(data.get('type', 'File')),
                properties=data.get('properties', {}),
                braille_id=data.get('braille_id', '')
            ))
            
        return results
        
    def traverse(self, start_id: str, rel_types: List[RelationType] = None,
                 max_depth: int = 3) -> List[Tuple[Node, List[Relationship]]]:
        """Traverse the graph from a starting node"""
        if start_id not in self.graph:
            return []
            
        results = []
        visited = set()
        
        def dfs(node_id: str, depth: int, path: List[Relationship]):
            if depth > max_depth or node_id in visited:
                return
                
            visited.add(node_id)
            node = self.get_node(node_id)
            if node:
                results.append((node, list(path)))
                
            for target in self.graph.successors(node_id):
                edge_data = self.graph.edges[node_id, target]
                edge_type = edge_data.get('type')
                
                if rel_types is None or edge_type in [r.value for r in rel_types]:
                    rel = Relationship(
                        id=edge_data.get('id', f"{node_id}->{target}"),
                        type=RelationType(edge_type) if edge_type else RelationType.CONTAINS,
                        source_id=node_id,
                        target_id=target,
                        properties=edge_data.get('properties', {})
                    )
                    dfs(target, depth + 1, path + [rel])
                    
        dfs(start_id, 0, [])
        return results
        
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics"""
        node_types = {}
        for node_id in self.graph.nodes():
            nt = self.graph.nodes[node_id].get('type', 'Unknown')
            node_types[nt] = node_types.get(nt, 0) + 1
            
        rel_types = {}
        for u, v, data in self.graph.edges(data=True):
            rt = data.get('type', 'Unknown')
            rel_types[rt] = rel_types.get(rt, 0) + 1
            
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_relationships": self.graph.number_of_edges(),
            "node_types": node_types,
            "relationship_types": rel_types,
            "is_connected": nx.is_weakly_connected(self.graph) if self.graph.number_of_nodes() > 0 else True,
            "braille_status": self.encoder.encode("graph_active")
        }


class Neo4jStore(GraphStore):
    """
    Production graph store using Neo4j.
    
    Requires Neo4j to be running.
    """
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 user: str = "neo4j", password: str = "password"):
        if not HAS_NEO4J:
            raise ImportError("neo4j driver required. Install with: pip install neo4j")
            
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.encoder = Braille8Encoder()
        self._init_constraints()
        
    def _init_constraints(self):
        """Create constraints and indexes"""
        with self.driver.session() as session:
            # Create constraints for each node type
            for nt in NodeType:
                try:
                    session.run(f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{nt.value}) REQUIRE n.id IS UNIQUE")
                except:
                    pass
                    
    def close(self):
        self.driver.close()
        
    def create_node(self, node: Node) -> Node:
        with self.driver.session() as session:
            query = f"""
                CREATE (n:{node.type.value} {{
                    id: $id,
                    braille_id: $braille_id,
                    created_at: datetime()
                }})
                SET n += $properties
                RETURN n
            """
            session.run(query, id=node.id, braille_id=node.braille_id, 
                       properties=node.properties)
        return node
        
    def get_node(self, node_id: str) -> Optional[Node]:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n {id: $id})
                RETURN n, labels(n) as labels
            """, id=node_id)
            
            record = result.single()
            if not record:
                return None
                
            n = record["n"]
            labels = record["labels"]
            
            props = dict(n)
            node_type = NodeType(labels[0]) if labels else NodeType.FILE
            
            return Node(
                id=props.pop("id"),
                type=node_type,
                properties=props,
                braille_id=props.pop("braille_id", "")
            )
            
    def update_node(self, node: Node) -> Node:
        with self.driver.session() as session:
            session.run(f"""
                MATCH (n:{node.type.value} {{id: $id}})
                SET n += $properties
                SET n.braille_id = $braille_id
                SET n.updated_at = datetime()
            """, id=node.id, properties=node.properties, braille_id=node.braille_id)
        return node
        
    def delete_node(self, node_id: str) -> bool:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n {id: $id})
                DETACH DELETE n
                RETURN count(n) as deleted
            """, id=node_id)
            return result.single()["deleted"] > 0
            
    def create_relationship(self, rel: Relationship) -> Relationship:
        with self.driver.session() as session:
            query = f"""
                MATCH (a {{id: $source_id}})
                MATCH (b {{id: $target_id}})
                CREATE (a)-[r:{rel.type.value} {{
                    id: $rel_id,
                    created_at: datetime()
                }}]->(b)
                SET r += $properties
                RETURN r
            """
            session.run(query, source_id=rel.source_id, target_id=rel.target_id,
                       rel_id=rel.id, properties=rel.properties)
        return rel
        
    def get_relationships(self, node_id: str, rel_type: RelationType = None,
                          direction: str = "both") -> List[Relationship]:
        with self.driver.session() as session:
            type_filter = f":{rel_type.value}" if rel_type else ""
            
            if direction == "out":
                query = f"MATCH (n {{id: $id}})-[r{type_filter}]->(m) RETURN r, n.id as source, m.id as target"
            elif direction == "in":
                query = f"MATCH (n {{id: $id}})<-[r{type_filter}]-(m) RETURN r, m.id as source, n.id as target"
            else:
                query = f"MATCH (n {{id: $id}})-[r{type_filter}]-(m) RETURN r, startNode(r).id as source, endNode(r).id as target"
                
            result = session.run(query, id=node_id)
            
            relationships = []
            for record in result:
                r = record["r"]
                relationships.append(Relationship(
                    id=r.get("id", ""),
                    type=RelationType(r.type),
                    source_id=record["source"],
                    target_id=record["target"],
                    properties=dict(r)
                ))
            return relationships
            
    def delete_relationship(self, rel_id: str) -> bool:
        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r {id: $id}]-()
                DELETE r
                RETURN count(r) as deleted
            """, id=rel_id)
            return result.single()["deleted"] > 0
            
    def query_nodes(self, node_type: NodeType = None,
                    properties: Dict[str, Any] = None) -> List[Node]:
        with self.driver.session() as session:
            type_label = f":{node_type.value}" if node_type else ""
            
            where_clauses = []
            params = {}
            if properties:
                for i, (k, v) in enumerate(properties.items()):
                    where_clauses.append(f"n.{k} = $prop_{i}")
                    params[f"prop_{i}"] = v
                    
            where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            query = f"MATCH (n{type_label}) {where} RETURN n, labels(n) as labels"
            result = session.run(query, **params)
            
            nodes = []
            for record in result:
                n = record["n"]
                labels = record["labels"]
                props = dict(n)
                
                nodes.append(Node(
                    id=props.pop("id"),
                    type=NodeType(labels[0]) if labels else NodeType.FILE,
                    properties=props,
                    braille_id=props.pop("braille_id", "")
                ))
            return nodes
            
    def traverse(self, start_id: str, rel_types: List[RelationType] = None,
                 max_depth: int = 3) -> List[Tuple[Node, List[Relationship]]]:
        with self.driver.session() as session:
            type_filter = "|".join([r.value for r in rel_types]) if rel_types else ""
            rel_pattern = f"[*1..{max_depth}]" if not type_filter else f"[:{type_filter}*1..{max_depth}]"
            
            query = f"""
                MATCH path = (start {{id: $id}})-{rel_pattern}->(end)
                RETURN nodes(path) as nodes, relationships(path) as rels
            """
            result = session.run(query, id=start_id)
            
            results = []
            for record in result:
                nodes = record["nodes"]
                rels = record["rels"]
                
                if nodes:
                    end_node = nodes[-1]
                    props = dict(end_node)
                    node = Node(
                        id=props.pop("id"),
                        type=NodeType(list(end_node.labels)[0]) if end_node.labels else NodeType.FILE,
                        properties=props,
                        braille_id=props.pop("braille_id", "")
                    )
                    
                    path = [
                        Relationship(
                            id=r.get("id", ""),
                            type=RelationType(r.type),
                            source_id=r.start_node.get("id"),
                            target_id=r.end_node.get("id"),
                            properties=dict(r)
                        ) for r in rels
                    ]
                    results.append((node, path))
                    
            return results
            
    def get_stats(self) -> Dict[str, Any]:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WITH labels(n) as labels, count(*) as cnt
                RETURN labels, cnt
            """)
            node_types = {r["labels"][0]: r["cnt"] for r in result if r["labels"]}
            
            result = session.run("""
                MATCH ()-[r]->()
                WITH type(r) as type, count(*) as cnt
                RETURN type, cnt
            """)
            rel_types = {r["type"]: r["cnt"] for r in result}
            
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            total_nodes = result.single()["nodes"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            total_rels = result.single()["rels"]
            
            return {
                "total_nodes": total_nodes,
                "total_relationships": total_rels,
                "node_types": node_types,
                "relationship_types": rel_types,
                "braille_status": self.encoder.encode("neo4j_active")
            }


def get_graph_store(backend: str = "networkx", **kwargs) -> GraphStore:
    """
    Factory function to get a graph store.
    
    Args:
        backend: "networkx" (default) or "neo4j"
        **kwargs: Backend-specific arguments
        
    Returns:
        GraphStore instance
    """
    if backend == "neo4j":
        return Neo4jStore(**kwargs)
    else:
        return NetworkXSQLiteStore(**kwargs)


# Convenience functions for IDE integration
def create_project_node(store: GraphStore, project_id: str, name: str) -> Node:
    """Create a project node"""
    return store.create_node(Node(
        id=project_id,
        type=NodeType.PROJECT,
        properties={"name": name, "created_at": datetime.now().isoformat()}
    ))


def create_file_node(store: GraphStore, file_id: str, name: str, 
                     language: str, content: str, project_id: str) -> Node:
    """Create a file node and link to project"""
    encoder = Braille8Encoder()
    
    node = store.create_node(Node(
        id=file_id,
        type=NodeType.FILE,
        properties={
            "name": name,
            "language": language,
            "content": content,
            "braille_content": encoder.encode(content),
            "line_count": content.count('\n') + 1
        }
    ))
    
    # Link to project
    store.create_relationship(Relationship(
        id=f"{project_id}-contains-{file_id}",
        type=RelationType.CONTAINS,
        source_id=project_id,
        target_id=file_id
    ))
    
    return node


def create_task_node(store: GraphStore, task_id: str, intent: str, 
                     status: str = "pending") -> Node:
    """Create a SAL Cascade task node"""
    return store.create_node(Node(
        id=task_id,
        type=NodeType.TASK,
        properties={
            "intent": intent,
            "status": status,
            "created_at": datetime.now().isoformat()
        }
    ))


def link_task_to_file(store: GraphStore, task_id: str, file_id: str):
    """Link a task to a file it generated"""
    store.create_relationship(Relationship(
        id=f"{task_id}-generated-{file_id}",
        type=RelationType.GENERATED,
        source_id=task_id,
        target_id=file_id
    ))


# Global store instance
_graph_store: Optional[GraphStore] = None

def get_store() -> GraphStore:
    """Get or create the global graph store"""
    global _graph_store
    if _graph_store is None:
        _graph_store = get_graph_store("networkx")
    return _graph_store
