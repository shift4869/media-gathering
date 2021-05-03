# coding: utf-8
import configparser
import logging.config
import os
import re

from abc import ABCMeta, abstractmethod
from logging import DEBUG, getLogger
from pathlib import Path


logger = getLogger("root")
logger.setLevel(DEBUG)


class LinkSearchBase():
    """リンク探索処理を担うクラス

    Notes:
        Chain of Responsibilityパターン

    Attributes:
        processer_list (LinkSearchBase[]): 処理担当者リスト
    """
    def __init__(self):
        self.processer_list = []
        pass

    def Register(self, processer) -> int:
        """担当者登録

        Args:
            processer (LinkSearchBase): 担当者

        Returns:
            int: 成功時0, 失敗時-1
        """
        interface_check = hasattr(processer, "IsTargetUrl") and hasattr(processer, "Process")
        if not interface_check:
            return -1
        self.processer_list.append(processer)
        return 0

    def CoRProcessDo(self, url) -> int:
        """処理実行メイン

        Notes:
            大元のLinkSearchBaseからのみ呼ばれる想定
            self.processer_listに担当者が登録されていないと処理されない

        Args:
            url (str): 処理対象url

        Returns:
            int: いずれかの担当者が処理を実行して成功した時0
                 担当者は見つかったが処理が失敗した時-1
                 担当者が見つからなかった時1
        """
        cor_result = 1  # 担当者発見フラグ
        proc_result = -1  # 処理成功フラグ

        # CoR
        for p in self.processer_list:
            if p.IsTargetUrl(url):
                cor_result = 0
                proc_result = p.Process(url)
                break  # 初めに見つかった担当者でのみ処理する
        
        # 返り値の意味はReturns参照
        return 1 if (cor_result == 1) else proc_result

    def CoRProcessCheck(self, url: str) -> bool:
        """処理実行確認

        Notes:
            大元のLinkSearchBaseからのみ呼ばれる想定。
            self.processer_listに登録されている、
            担当者のいずれかが処理できるかどうかを返す。
            実際に処理は行わない。

        Args:
            url (str): 処理対象url

        Returns:
            bool: 処理できるいずれかの担当者が見つかった時True
                  処理できる担当者が見つからなかった時False
        """
        cor_result = 1  # 担当者発見フラグ

        # CoR
        for p in self.processer_list:
            if p.IsTargetUrl(url):
                cor_result = 0
                break
        
        # 返り値の意味はReturns参照
        return (cor_result == 0)

    def IsTargetUrl(self, url) -> bool:
        """自分（担当者）が処理できるurlかどうか返す関数

        Notes:
            派生クラスでオーバーライドする
            基底クラスでは常にFalseを返す

        Args:
            url (str): 処理対象url

        Returns:
            bool: 担当urlだった場合True, そうでない場合False
        """
        return False

    def Process(self, url: str) -> int:
        """自分（担当者）が担当する処理

        Notes:
            派生クラスでオーバーライドする
            基底クラスでは常に何もせず、失敗扱いとする

        Args:
            url (str): 処理対象url
            save_base (str): 保存先ベースパス

        Returns:
            int: 成功時0, 失敗時-1
        """
        return -1


class ConcreteLinkSearch(LinkSearchBase):
    def __init__(self):
        super().__init__()
        pass
    
    def IsTargetUrl(self, url) -> bool:
        logger.debug("ConcreteLinkSearch IsTargetUrl called")
        return False

    def Process(self, url: str) -> int:
        logger.debug("ConcreteLinkSearch Process called")
        return 0


if __name__ == "__main__":
    lsb = LinkSearchBase()
    url = "https://www.pixiv.net/artworks/86704541"
    url = "http://nijie.info/view_popup.php?id=409587"

    # 最低限実装した担当者を登録（何も処理しない）
    pls = ConcreteLinkSearch()
    lsb.Register(pls)

    CONFIG_FILE_NAME = "./config/config.ini"
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_NAME, encoding="utf8")

    # pixivURLを処理する担当者を登録
    if config["pixiv"].getboolean("is_pixiv_trace"):
        from PictureGathering import LSPixiv
        lsp = LSPixiv.LSPixiv(config["pixiv"]["username"], config["pixiv"]["password"], config["pixiv"]["save_base_path"])
        lsb.Register(lsp)

    # nijieURLを処理する担当者を登録
    if config["nijie"].getboolean("is_nijie_trace"):
        from PictureGathering import LSNijie
        lsn = LSNijie.LSNijie(config["nijie"]["email"], config["nijie"]["password"], config["nijie"]["save_base_path"])
        lsb.Register(lsn)

    # CoR実行
    res = lsb.CoRProcessCheck(url)
    res = lsb.CoRProcessDo(url)
    pass
    pass
