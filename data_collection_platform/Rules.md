# Rules of the Collaborative game
![image](https://user-images.githubusercontent.com/5908392/121846837-a4258000-ccb5-11eb-860c-92c8fdca53d2.png)

**Goal:** 
Two players are required to collaboratively build a provided target structure using verbal interactions, as shown in the Figure above. A player can be assigned only one of the following roles:

* *Architect*, who can see the required target structure specified by the task. Their main goal is to explain structure using natural language in dialogue style:      
* *Builder*, who cannot see the target structure. Their main goal is to follow the step-by-step instructions given by Architect to build the target structure utilizing provided inventory. When instructions are not clear, Builder can offer an option to ask clarifying questions in cases. 
    
*Architect* can do the following:   
* can observe: 
   * the partial structure that has been built at the last interaction
   * the structure that has been built before the last instruction
   * the previous instruction
* has a view to the ongoing structure from 4 different angels
* given target structure and the current state of the needs provide the instruction for the Builder what to do next
* evaluates the previous interaction:
   * if at the previous step the Builder moved blocks, Architect needs to evaluate the Builder action using a 5-point scale
   * if at the previous step the Builder asked the clarifying question (example in Figure above) instead of moving blocks, Architect can see the previous instruction and the ongoing structure and needs:
      * to evaluate if the question was reasonable
      * to answer the question to clarify the previous instruction
* can stop the game if the structure is completed. In this case, the Architect is asked to describe how close the structure is and provide a textual explanation of why the game should be stopped, e.g., `we have almost reached a target structure, but purple blocks should be orange,` `we need to stop the game because it is not possible to fix it any.`
    
    
*Builder* can do the following:
* has NO access to the target structure
* sees the structure that has been build so far
* has the same view of the game where the last Builder left
* sees the textual instruction from the Architect, and the angle Artichect picked while providing the instruction
* can ask clarifying questions about the instruction in case it is not clear
* evaluates the provided instruction based on 5-point-scale 


*Bonuses* for Architect
* a player who was evaluated high by other players in the Builder role will get a special Bonus for HIT

*Bonuses* for Builder
* a player who was evaluated high by other players in Architect role will get a special Bonus for HIT
