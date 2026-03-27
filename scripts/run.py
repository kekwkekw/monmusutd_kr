from update import Updater

if __name__ == '__main__':
    # montrans 루트와 gt_input 경로 설정
    Updater(
        translation_dir='.',
        download_dir='MonTransl/sampleProject/gt_input'
    ).run()