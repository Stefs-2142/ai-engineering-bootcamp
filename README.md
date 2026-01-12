# ai-engineering-bootcamp-sprint-0

We strongly recomend you coding along the videos available on Maven platform rather than just cloning the repository and running the code.

If you do need to run the code, this is how:

- Clone the repository.
- Run:
```bash
cp env.example .env
```

Edit `.env` and add your API keys:

```
OPENAI_API_KEY=your_google_api_key
GOOGLE_API_KEY=your_google_api_key
GROQ_API_KEY=your_groq_api_key
```
Keep the remaining configuration as per ```.env.example```.


#### To run the project, execute:

```bash
make run-docker-compose
```

Streamlit application: http://localhost:8501

FastAPI documentation: http://localhost:8000/docs



## Contact

If you have any questions, feel free to contact me via aurimas@swirlai.com

You can also find me on:

- 🔗 [LinkedIn](https://www.linkedin.com/in/aurimas-griciunas)
- 🔗 [X](https://x.com/Aurimas_Gr)
- 🔗 [Newsletter](https://www.newsletter.swirlai.com/)

## This repository uses data provided by the authors of the following paper.
If you use this work, please cite:

```
@article{hou2024bridging,
  title={Bridging Language and Items for Retrieval and Recommendation},
  author={Hou, Yupeng and Li, Jiacheng and He, Zhankui and Yan, An and Chen, Xiusi and McAuley, Julian},
  journal={arXiv preprint arXiv:2403.03952},
  year={2024}
}
```