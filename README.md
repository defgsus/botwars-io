# garage @ home for [botwars.io](https://botwars.io/)

In the *mood of procrastination* i came across the [botwars.io](https://botwars.io/)
website and my ego said: *'Dude, you will write the best robot there, just by diligence!'*

Well ... guess i have spent already too much time on this. But some nice little framework
came out:

To test your bots against each other call:

```bash
python match.py randy randy2
```

`randy` and `randy2` are two example bots contained in the
[src/bots/](src/bots) directory. To make, e.g. a hundred matches, simply add
the `--many 100` option.


### internals

The [botwars.io rules say](https://botwars.io/Documentation/Sandbox) that
the program will be executed for each single round of the match. This increases
the CPU time a lot when running many local matches. However, when using the 
`GameBase` class from [src/bots/botbase.py](src/bots/botbase.py) the module will
be imported and only a class instance is created in each round, which makes
things **a lot** faster.

Depending on the bot algorithms a match can be done in 2 seconds (using, e.g. A* search)
down to 200 milliseconds (for stupid ones like [randy](src/bots/randy.py)).
 


