# GENIE-OPS-Prototype

fixed the deletion button not working
note to the CTO :
in case you got to review the code base before i fix the issue with opening the form url and parsing the html for fields to fill
the test folder in the backend dir has a run_test.bat that runs the script responsible for parsing the DOM with or without the LLM

the tests were success ,  ollama did figure the names of the fields and the form was filled  but when implementing it to the main app , i faced problems with playwright working on a different thread from the main backend and causing issues like not opening the chromium properly , starting the parsing when the html  it didn't fully  render yet , etc.
main
