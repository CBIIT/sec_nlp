import argparse

import evaluate
import numpy as np
from datasets import load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="ChrisLiewJY/BERTweet-Hedge")
    parser.add_argument("--dataset_name", type=str, required=True)
    parser.add_argument("--task_name", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="./results")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=3e-5)
    args = parser.parse_args()

    # Load dataset
    dataset = load_dataset(args.dataset_name, args.task_name)

    # Load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name, num_labels=len(dataset["train"].features["label"].names)
    )

    # Preprocess data
    def preprocess_function(examples):
        if "text" in examples:
            return tokenizer(examples["text"], truncation=True)
        elif "sentence1" in examples and "sentence2" in examples:
            return tokenizer(
                examples["sentence1"], examples["sentence2"], truncation=True
            )
        else:
            raise ValueError(
                "Dataset must contain 'text' or 'sentence1' and 'sentence2' columns."
            )

    encoded_dataset = dataset.map(preprocess_function, batched=True)

    metric = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return metric.compute(predictions=predictions, references=labels)

    # Define training arguments
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        evaluation_strategy="epoch",
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        report_to="none",
    )

    # Create Trainer instance
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=encoded_dataset["train"],
        eval_dataset=encoded_dataset["validation"]
        if "validation" in encoded_dataset
        else encoded_dataset["test"],
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    # Train and evaluate
    trainer.train()
    trainer.evaluate()


if __name__ == "__main__":
    main()
