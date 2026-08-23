# Model Answer Paper

## Q1. Explain Data Structures and classify them into Linear and Non-Linear Data Structures. Give suitable examples. [10 Marks]

A **data structure** is a specialized method of organizing, storing, and managing data in computer memory so that the data can be accessed, processed, searched, inserted, deleted, and updated efficiently. The choice of an appropriate data structure affects the efficiency and performance of an algorithm and a computer program.

Data structures are broadly classified into **Linear Data Structures** and **Non-Linear Data Structures**.

### 1. Linear Data Structures

In a **linear data structure**, data elements are arranged sequentially or in a linear order. Generally, each element is connected to its previous and/or next element.

Examples include:

- **Array:** A collection of elements of the same data type stored in contiguous memory locations. Elements can be directly accessed using an index.
- **Linked List:** A collection of nodes where each node contains data and a reference or pointer to the next node. Nodes do not necessarily occupy contiguous memory locations.
- **Stack:** A linear data structure that follows the **LIFO (Last In, First Out)** principle. Insertion and deletion are performed from the same end called the top.
- **Queue:** A linear data structure that follows the **FIFO (First In, First Out)** principle. Elements are inserted at the rear and removed from the front.

### 2. Non-Linear Data Structures

In a **non-linear data structure**, elements are not arranged sequentially. Elements can have hierarchical, branching, or network-like relationships.

Examples include:

- **Tree:** A hierarchical data structure consisting of nodes connected through edges. It contains a root node and may have parent-child relationships. Examples include Binary Trees and Binary Search Trees.
- **Graph:** A collection of vertices or nodes connected by edges. Graphs are useful for representing networks such as road networks, social networks, and computer networks.

### Difference

Linear data structures organize elements in a sequential manner, while non-linear data structures organize elements in hierarchical or interconnected relationships.

Therefore, data structures provide an efficient way of storing and manipulating data and are fundamental to designing efficient algorithms and software systems.

---

## Q2. Define an Algorithm. Explain the characteristics of a good algorithm. [10 Marks]

An **algorithm** is a finite sequence of well-defined, logical, and step-by-step instructions used to solve a particular problem or perform a specific task. An algorithm accepts input, processes it according to a defined procedure, and produces the required output.

A good algorithm should have the following characteristics:

### 1. Input

An algorithm may accept **zero or more inputs**. The input values required by the algorithm should be clearly defined.

### 2. Output

An algorithm should produce **at least one clearly defined output**. The output should represent the result of solving the given problem.

### 3. Definiteness

Every step of an algorithm must be **clear, precise, and unambiguous**. There should be no confusion about what operation needs to be performed.

### 4. Finiteness

An algorithm must terminate after a **finite number of steps**. It should not continue executing indefinitely.

### 5. Effectiveness

Every operation in an algorithm should be **basic, practical, and executable** using available resources. The instructions should be possible to perform within a reasonable amount of time.

### 6. Correctness

An algorithm should produce the **correct result for valid inputs**. An algorithm that produces incorrect results cannot be considered a valid solution.

### 7. Language Independence

An algorithm describes the logic of solving a problem and should not depend on a particular programming language. The same algorithm can generally be implemented using languages such as C, C++, Java, or Python.

### 8. Deterministic Behavior

For the same valid input, the algorithm should follow a well-defined sequence of operations and produce the expected result.

Thus, an algorithm provides a systematic and logical procedure for solving computational problems efficiently and correctly.

---

## Q3. What is Complexity Analysis? Explain Time Complexity and Space Complexity. Also explain Best, Average and Worst Case analysis. [10 Marks]

**Complexity analysis** is the process of evaluating the efficiency of an algorithm by studying the resources required by the algorithm as the size of the input increases.

The two major types of complexity are **Time Complexity** and **Space Complexity**.

### 1. Time Complexity

**Time complexity** measures how the number of operations or execution time of an algorithm grows as the input size increases.

It is commonly represented using **Big-O notation**, such as:

- **O(1)** – Constant time
- **O(log n)** – Logarithmic time
- **O(n)** – Linear time
- **O(n log n)** – Linearithmic time
- **O(n²)** – Quadratic time

For example, accessing an element of an array using its index generally takes **O(1)** time, while searching sequentially through an unsorted array can take **O(n)** time.

### 2. Space Complexity

**Space complexity** measures the amount of memory required by an algorithm during execution.

It may include memory required for:

- Variables
- Data structures
- Arrays
- Recursion
- Temporary or auxiliary storage

An algorithm that requires less additional memory has lower space requirements.

### Cases of Complexity Analysis

#### 1. Best Case

The **best case** represents the minimum amount of resources required by an algorithm for a particular input.

For example, in linear search, if the required element is the first element, the search can finish immediately.

Best-case analysis is commonly associated with the lower bound and may be represented using **Omega (Ω)** notation.

#### 2. Average Case

The **average case** represents the expected resource requirement when considering typical or possible inputs.

It attempts to determine how the algorithm performs under normal or average conditions.

#### 3. Worst Case

The **worst case** represents the maximum amount of resources required by an algorithm for an input of a particular size.

For example, in linear search, if the required element is at the last position or is not present, the algorithm may need to examine all elements.

Worst-case complexity is commonly represented using **Big-O (O)** notation.

Therefore, complexity analysis helps programmers compare algorithms and select an appropriate solution based on execution time and memory requirements.

---

## Q4. Explain Array and Linked List. Compare them based on memory allocation, access, insertion/deletion and size. [10 Marks]

### Array

An **array** is a linear data structure that stores a collection of elements, generally of the same data type, in **contiguous memory locations**.

Each element can be accessed using an **index**.

Example:

```text
Array = [10, 20, 30, 40, 50]

Index =   0   1   2   3   4