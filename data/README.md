# Frozen phase-two inputs

`phase2_conversations.json` contains a deterministic selection of complete multi-turn rows from the public MIT-licensed [UltraChat 200k dataset](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k). The file retains its selection rule and source URL. This dataset contains generated dialogue. It is not a production trace or a corpus of human conversations.

The benchmark records row identifiers, token clipping, any concatenation of distinct conversations, and the fixture hash. The original dataset is described in [Enhancing Chat Language Models by Scaling High-quality Instructional Conversations](https://arxiv.org/abs/2305.14233).

`model_configs.json` records public configuration lookups used to plan the study. The benchmark independently loads each actual model configuration and verifies KV tensor sizes. A configuration lookup alone is not a GPU calibration or a model measurement. Access failures are preserved.
