## Evaluate a builder

In this task, you will be evaluating a builder who was given a set of plain text instructions, a partially built 
structure and 45 seconds to execute the instructions. The result of executing the instructions can be one of two things:
1. A new structure on top of the partially built structure or </br>
2. The builder asked a clarification question because things weren't clear.  

In this task, you are being asked to evaluate how the builder did, given the instructions, the input partial structure 
and the output of that execution. </br>
You are asked to **evaluate the builder on a scale of 1 to 5** as explained below: </br>
#### If the output of the builder's task was a new structure:
**1. Very poor : The builder didn't execute what was asked.** </br>
**2. Poor: The builder only partially executed what was asked.**</br>
**3. Acceptable: The builder did what was doable given the instructions and world state.**</br>
**4. Great: The builder executed the instructions exactly as was asked.**</br>
**5. Fantastic: The builder executed the instructions really well, it couldn't have been done any better.**</br>

#### If the output of the builder's task was a clarification question:
**1. Very poor : The builder asked a question that was unreasonable.** </br>
**2. Poor: The builder asked a question that didn't quite make sense.**</br>
**3. Acceptable: The builder asked a reasonable question given the partial state and instruction.**</br>
**4. Great: The instructions were unclear and the builder asked the right question.**</br>
**5. Fantastic: There was no way to execute the instructions other than asking the question the builder asked.**</br>

### Examples
1. For example, for a builder who got the following as input: </br>
**World**:
![image](https://drive.google.com/uc?export=view&id=1IvkIPk2qvsnGzNnYb2wT06-S3Bmtt1Pe)

**Instruction: "place an orange block on top of the blue block"**</br>

**Output**:
![image](https://drive.google.com/uc?export=view&id=13bpVlGtIjDNV7R-W5i2yeJ1Iwlbn2Bnr)

The building created a new state of the structure and the expected rating would be **anywhere between 3-5**. (acceptable, great and fantastic all work!)

2. For example, for a builder who got the following as input: </br>
**World**:
![image](https://drive.google.com/uc?export=view&id=13bpVlGtIjDNV7R-W5i2yeJ1Iwlbn2Bnr)

**Instruction: "place a blue block to the right of the orange block"**</br>

**Output**:
"Should I place the blue block touching the orange block on its right or in the air 
anywhere to its right ?"

The builder asked a clarification question and the expected rating would be 4 (great) 
since it wasn't clear exactly what the arrangement of the new blue block would be with 
respect to orange block. 

3. For example, for a builder who got the following as input: </br>
**World**:
![image](https://drive.google.com/uc?export=view&id=17mdYgkK0wrFaQzH0D31t24vDkdFwkM1Q)

**Instruction: "put an orange block in the space between the two blue blocks"**</br>

**Output**:
![image](https://drive.google.com/uc?export=view&id=13bpVlGtIjDNV7R-W5i2yeJ1Iwlbn2Bnr)

The expected rating would be 1 (very poor) since the builder destroyed a block and didn't do what was asked.
