import os
import torch
import torchvision
import yaml
from dataset.data_loader import get_test_SR_data
from torch.utils.data import DataLoader
from utils.dir_utils import mkdir, get_last_path
from utils.model_utils import load_checkpoint
from model.URSCT_SR_model import URSCT_SR
from tqdm import tqdm
from utils.image_utils import torchPSNR, torchSSIM
import torchvision.transforms.functional as TF

def get_dataloader(opt_test):
    test_dataset = get_test_SR_data(opt_test['TEST_DIR'], {'patch_size': opt_test['TEST_PS']},
                                    scale=opt['MODEL_DETAIL']['SCALE'])
    return DataLoader(dataset=test_dataset, batch_size=1, shuffle=False, num_workers=opt_test['NUM_WORKS'],
                      drop_last=False)

def predict_save(test_loader, opt_test):
    '''
    use model to predict, save the result, and evaluate
    '''
    for i, data in enumerate(tqdm(test_loader)):
        input = data[0].to(device)
        target_SR = data[1].to(device)
        with torch.no_grad():
            restored_SR = model(input)
        torchvision.utils.save_image(torch.cat( (TF.resize(input[0],opt_test['TEST_PS']),
                                                 restored_SR[0],target_SR[0]), -1),
                                     os.path.join(result_dir, str(i) + '.png'))

def predict_save_eval(test_loader, opt_test):
    '''
    use model to predict, save the result, and evaluate
    '''
    PSNRs, SSIMs = [], []
    for i, data in enumerate(tqdm(test_loader)):
        input = data[0].to(device)
        target_SR = data[1].to(device)
        with torch.no_grad():
            restored_SR = model(input)
        PSNRs.append(torchPSNR(restored_SR,target_SR))
        SSIMs.append(torchSSIM(restored_SR, target_SR))
        torchvision.utils.save_image(torch.cat( (TF.resize(input[0],opt_test['TEST_PS']),
                                                 restored_SR[0],target_SR[0]), -1),
                                     os.path.join(result_dir, str(i) + '.png'))
    return PSNRs, SSIMs



if __name__ == '__main__':
    with open('../configs/Enh&SR_opt.yaml', 'r') as config:
        opt = yaml.safe_load(config)
        opt_test = opt['TEST']
    device = opt_test['DEVICE']
    model_detail_opt = opt['MODEL_DETAIL']
    result_dir = os.path.join(opt_test['SAVE_DIR'], opt['TRAINING']['MODEL_NAME'], 'test_results')
    mkdir(result_dir)

    model = URSCT_SR(model_detail_opt).to(device)
    path_chk_rest = get_last_path(os.path.join(opt_test['SAVE_DIR'], opt['TRAINING']['MODEL_NAME'], 'models'), '_bestSSIM.pth')
    load_checkpoint(model, path_chk_rest)
    model.eval()

    test_loader = get_dataloader(opt_test)
    PSNRs, SSIMs = predict_save_eval(test_loader, opt_test)
    # predict_save(test_loader, opt_test)
    print("[PSNR] mean: {:.4f} std: {:.4f}".format(torch.stack(PSNRs).mean().item(), torch.stack(PSNRs).std().item()))
    print("[SSIM] mean: {:.4f} std: {:.4f}".format(torch.stack(SSIMs).mean().item(), torch.stack(SSIMs).std().item()))
