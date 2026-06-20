import logging
from pathlib import Path
from dataclasses import dataclass, field

import mlflow
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType

from .dataset import build_dataset, tokenize_dataset, BASE_MODEL

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class TrainConfig:
    base_model: str = BASE_MODEL
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    target_modules: list[str] = field(default_factory=lambda: ["q", "v"])
    epochs: int = 5
    batch_size: int = 4
    learning_rate: float = 3e-4
    warmup_steps: int = 50
    weight_decay: float = 0.01
    max_input_len: int = 256
    max_target_len: int = 512
    output_dir: str = str(MODEL_DIR / "checkpoints")
    adapter_dir: str = str(MODEL_DIR / "lora_adapter")


def run_training(config: TrainConfig, progress_callback=None) -> dict:
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    logger.info(f"Training on device: {device}")

    if progress_callback:
        progress_callback(5, "Loading dataset")

    dataset = build_dataset()
    tokenizer = AutoTokenizer.from_pretrained(config.base_model)
    tokenized = tokenize_dataset(dataset, tokenizer)

    if progress_callback:
        progress_callback(15, "Loading base model")

    base_model = AutoModelForSeq2SeqLM.from_pretrained(config.base_model)

    lora_config = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.target_modules,
        bias="none",
    )

    model = get_peft_model(base_model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    logger.info(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    training_args = Seq2SeqTrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        warmup_steps=config.warmup_steps,
        weight_decay=config.weight_decay,
        learning_rate=config.learning_rate,
        predict_with_generate=True,
        generation_max_length=config.max_target_len,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        logging_steps=10,
        report_to=[],
        fp16=(device == "cuda"),
    )

    collator = DataCollatorForSeq2Seq(tokenizer, model=model, pad_to_multiple_of=8)

    if progress_callback:
        progress_callback(20, "Starting training")

    mlflow.set_experiment("immigration-ai-flan-t5-lora")
    with mlflow.start_run() as run:
        mlflow.log_params(
            {
                "base_model": config.base_model,
                "lora_r": config.lora_r,
                "lora_alpha": config.lora_alpha,
                "epochs": config.epochs,
                "batch_size": config.batch_size,
                "lr": config.learning_rate,
            }
        )

        trainer = Seq2SeqTrainer(
            model=model,
            args=training_args,
            train_dataset=tokenized["train"],
            eval_dataset=tokenized["validation"],
            tokenizer=tokenizer,
            data_collator=collator,
        )

        trainer.train()

        if progress_callback:
            progress_callback(85, "Evaluating")

        eval_results = trainer.evaluate(tokenized["test"])
        mlflow.log_metrics({"test_loss": eval_results["eval_loss"]})

    if progress_callback:
        progress_callback(90, "Saving adapter")

    adapter_path = Path(config.adapter_dir)
    adapter_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(adapter_path))
    tokenizer.save_pretrained(str(adapter_path))
    logger.info(f"LoRA adapter saved to {adapter_path}")

    if progress_callback:
        progress_callback(100, "Done")

    return {
        "test_loss": eval_results["eval_loss"],
        "adapter_path": str(adapter_path),
        "mlflow_run_id": run.info.run_id,
    }
