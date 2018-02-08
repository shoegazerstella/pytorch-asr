#!python
import torch
from torch.autograd import Variable
from pyro.shim import parse_torch_version

from utils.logger import logger, set_logfile
from utils.audio import AudioDataset

from model import SsVae
from aspire import NUM_PIXELS, NUM_LABELS

MODEL_SUFFIX = "pth.tar"


class PredictLoader(AudioDataset):

    def __init__(self, use_cuda=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_cuda = use_cuda

    def load(self, wav_file):
        # read and transform wav file
        if self.transform is not None:
            tensor = self.transform(wav_file)
        tensor = torch.stack(tensor)
        if self.use_cuda:
            tensor = tensor.cuda()
        return tensor


def predict(args):
    # load model
    ss_vae = SsVae(x_dim=NUM_PIXELS, y_dim=NUM_LABELS, **vars(args))

    for wav_file in args.wav_files:
        # prepare data
        data_loader = PredictLoader(use_cuda=args.use_cuda, resample=True, sample_rate=8000,
                                    frame_margin=4, unit_frames=9)
        xs = data_loader.load(wav_file)
        xs = Variable(xs)
        # classify phones
        with torch.no_grad():
            alpha = ss_vae.classifier(xs)

        res, phn_idx = torch.topk(alpha, 1)
        phns = list(torch.squeeze(phn_idx).cpu().numpy())
        logger.info(f"prediction of {wav_file}: {phns}")


if __name__ == "__main__":
    import sys
    import argparse
    from pathlib import Path

    import torch

    parser = argparse.ArgumentParser(description="SS-VAE model prediction")
    parser.add_argument('--use-cuda', default=False, action='store_true', help="use cuda")
    parser.add_argument('--log-dir', default='./logs', type=str, help="filename for logging the outputs")
    parser.add_argument('--continue-from', type=str, help="model file path to make continued from")
    parser.add_argument('wav_files', type=str, nargs='+', help="list of wav_files for prediction")

    args = parser.parse_args()

    # some assertions to make sure that batching math assumptions are met
    assert parse_torch_version() >= (0, 2, 1), "you need pytorch 0.2.1 or later"

    set_logfile(Path(args.log_dir, "predict.log"))

    logger.info(f"Prediction started with command: {' '.join(sys.argv)}")
    args_str = [f"{k}={v}" for (k, v) in vars(args).items()]
    logger.info(f"args: {' '.join(args_str)}")

    if args.use_cuda:
        torch.set_default_tensor_type("torch.cuda.FloatTensor")

    # run training
    predict(args)
